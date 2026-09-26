import AppKit
import Security

/// Values never enter WebKit, a subprocess, an argument list or the metadata registry.
enum SecretVault {
    static let registry=FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/AI Control Studio/secret-references.json")
    static func entries() throws -> [[String:Any]] {
        var rows:[[String:Any]]=[
            ["id":"openrouter","label":"OpenRouter","service":"ai-control-studio.secret.openrouter","account":NSUserName(),"readonly":false,"purpose":"Jev decision API"],
            ["id":"tavily","label":"Tavily API key","service":"ai-control-studio.secret.tavily","account":NSUserName(),"readonly":false,"purpose":"Optional Tavily API credential"],
            ["id":"claude-oauth","label":"Claude Code OAuth credentials","service":"Claude Code-credentials","account":"","readonly":true,"purpose":"Managed by Claude Code; includes MCP sign-ins"]]
        if FileManager.default.fileExists(atPath:registry.path) {
            guard let custom=try JSONSerialization.jsonObject(with:Data(contentsOf:registry)) as? [[String:Any]] else {throw failure("Secret reference registry is invalid.")}
            for item in custom {
                guard let id=item["id"] as? String,let service=item["service"] as? String,service=="ai-control-studio.secret."+id,!rows.contains(where:{$0["id"] as? String==id}) else {throw failure("Invalid managed Keychain reference.")}
                rows.append(item)
            }
        }
        return rows
    }
    static func query(_ row:[String:Any])->[String:Any] {
        var q:[String:Any]=[kSecClass as String:kSecClassGenericPassword,kSecAttrService as String:row["service"]!]
        if let account=row["account"] as? String,!account.isEmpty {q[kSecAttrAccount as String]=account}
        return q
    }
    static func list() throws -> [String:Any] {
        let rows=try entries().map {original -> [String:Any] in
            var row=original,q=query(row);q[kSecReturnAttributes as String]=true;q[kSecMatchLimit as String]=kSecMatchLimitOne
            var result:CFTypeRef?;let code=SecItemCopyMatching(q as CFDictionary,&result)
            row["status"]=code==errSecSuccess ? "Available":code==errSecItemNotFound ? "Not stored":code==errSecInteractionNotAllowed ? "Keychain locked":"Check failed"
            row["storage"]="macOS default Keychain";return row
        }
        return ["ok":true,"entries":rows,"registry":registry.path]
    }
    static func store(_ row:[String:Any],value:String) throws {
        guard !value.isEmpty,value.utf8.count<=65536 else {throw failure("Enter a nonempty secret up to 64 KB.")}
        let q=query(row);let update:[String:Any]=[kSecValueData as String:Data(value.utf8),kSecAttrLabel as String:"AI Control Studio · "+(row["label"] as? String ?? "Secret")]
        var code=SecItemUpdate(q as CFDictionary,update as CFDictionary)
        if code==errSecItemNotFound {code=SecItemAdd(q.merging(update,uniquingKeysWith:{$1}) as CFDictionary,nil)}
        guard code==errSecSuccess else {throw failure("Keychain did not save the secret: "+(SecCopyErrorMessageString(code,nil) as String? ?? String(code)))}
    }
    static func updateRegistry(_ rows:[[String:Any]]) throws {
        try FileManager.default.createDirectory(at:registry.deletingLastPathComponent(),withIntermediateDirectories:true)
        try JSONSerialization.data(withJSONObject:rows,options:[.prettyPrinted,.sortedKeys]).write(to:registry,options:.atomic)
        try FileManager.default.setAttributes([.posixPermissions:0o600],ofItemAtPath:registry.path)
    }
    static func edit(_ ident:String?) throws -> [String:Any] {
        let existing=try entries();let custom=existing.filter {($0["service"] as? String ?? "").hasPrefix("ai-control-studio.secret.")}
        var row:[String:Any]
        if let id=ident {
            guard let found=existing.first(where:{$0["id"] as? String==id}),found["readonly"] as? Bool != true else {throw failure("This credential is managed by its client.")}
            row=found
        } else {
            let id=UUID().uuidString.lowercased();row=["id":id,"label":"","service":"ai-control-studio.secret."+id,"account":NSUserName(),"readonly":false,"purpose":"Custom API credential"]
        }
        let alert=NSAlert();alert.messageText=ident==nil ? "Add a Keychain secret":"Set \(row["label"] as? String ?? "secret")"
        alert.informativeText="The value is saved directly to macOS Keychain. Configuration files contain only its reference. Existing values are never displayed."
        let view=NSView(frame:NSRect(x:0,y:0,width:420,height:110));let name=NSTextField(frame:NSRect(x:0,y:76,width:420,height:26));name.placeholderString="Secret name";name.stringValue=row["label"] as? String ?? "";name.isEditable=ident==nil
        let password=NSSecureTextField(frame:NSRect(x:0,y:28,width:420,height:28));password.placeholderString="Paste the API key here"
        view.addSubview(name);view.addSubview(password);alert.accessoryView=view;alert.addButton(withTitle:"Save to Keychain");alert.addButton(withTitle:"Cancel")
        guard alert.runModal() == .alertFirstButtonReturn else{return ["ok":true,"cancelled":true]}
        defer {password.stringValue=""}
        let label=name.stringValue.trimmingCharacters(in:.whitespacesAndNewlines)
        guard !label.isEmpty,label.count<=100 else {throw failure("Use a secret name of 1–100 characters.")}
        if ident==nil && existing.contains(where:{($0["label"] as? String ?? "").caseInsensitiveCompare(label) == .orderedSame}) {throw failure("A secret with that name already exists.")}
        row["label"]=label
        // Save metadata first for new items so a registry failure cannot orphan a value.
        if ident==nil {try updateRegistry(custom+[row])}
        do {try store(row,value:password.stringValue)} catch {if ident==nil {try? updateRegistry(custom)};throw error}
        return ["ok":true,"id":row["id"]!,"message":"Secret saved in macOS Keychain. Its value was not written to a configuration file."]
    }
    static func remove(_ ident:String) throws -> [String:Any] {
        let all=try entries();guard let row=all.first(where:{$0["id"] as? String==ident}),row["readonly"] as? Bool != true else {throw failure("This credential is managed by its client.")}
        let alert=NSAlert();alert.messageText="Remove \(row["label"] as? String ?? "secret") from Keychain?";alert.informativeText="This deletes the stored value. Any configuration referencing it will need a replacement. You can add a new value later."
        alert.addButton(withTitle:"Remove secret");alert.addButton(withTitle:"Cancel")
        guard alert.runModal() == .alertFirstButtonReturn else{return ["ok":true,"cancelled":true]}
        let code=SecItemDelete(query(row) as CFDictionary)
        guard code==errSecSuccess || code==errSecItemNotFound else {throw failure("Keychain could not remove this secret.")}
        // Keep its reference so missing values remain visible and repairable.
        return ["ok":true,"message":"Secret value removed. Its reference is retained for replacement."]
    }
    static func failure(_ text:String)->NSError {NSError(domain:"AI Control Studio",code:1,userInfo:[NSLocalizedDescriptionKey:text])}
}
