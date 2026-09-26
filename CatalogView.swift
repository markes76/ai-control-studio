import AppKit
import UniformTypeIdentifiers

final class CatalogView: NSView, NSTableViewDataSource, NSTableViewDelegate, NSSearchFieldDelegate {
    var entries = [[String:Any]](), filtered = [[String:Any]]()
    let search = NSSearchField(), filter = NSPopUpButton(), table = NSTableView()
    let detail = NSTextField(wrappingLabelWithString: "Select a connector to see its connection details.")
    let status = NSTextField(labelWithString: "Loading directory…")
    let desktop = NSButton(checkboxWithTitle: "Claude Desktop (gateway)", target:nil, action:nil)
    let code = NSButton(checkboxWithTitle: "Claude Code CLI", target:nil, action:nil)
    let detailLogo=NSImageView()
    let inspectorTitle=Studio.text("Choose a connector",NSRect(x:693,y:392,width:265,height:54),17,.semibold,Studio.navy)
    let inspectorAuthor=Studio.text("",NSRect(x:628,y:360,width:335,height:23),12,.regular,Studio.muted)
    var buttons = [NSButton]()
    override init(frame: NSRect) {
        super.init(frame:frame)
        wantsLayer=true;layer?.backgroundColor=Studio.paper.cgColor
        addSubview(Studio.text("Find your next tool",NSRect(x:22,y:540,width:630,height:42),28,.semibold,Studio.navy))
        addSubview(Studio.text("Browse providers, choose a connection, and configure your clients.",NSRect(x:22,y:515,width:1020,height:24),13,.regular,Studio.muted))
        search.frame=NSRect(x:22,y:467,width:520,height:32);search.placeholderString="Search connectors, providers, or categories";search.delegate=self;addSubview(search)
        filter.frame=NSRect(x:555,y:467,width:220,height:32);filter.addItems(withTitles:["All MCPs","Remote servers","Local servers & extensions","Registered"]);filter.target=self;filter.action=#selector(filterChanged);addSubview(filter)
        button("Refresh directory",#selector(refresh),NSRect(x:790,y:466,width:175,height:34))
        let scroll=NSScrollView(frame:NSRect(x:22,y:88,width:560,height:360));scroll.hasVerticalScroller=true;scroll.borderType = .noBorder;scroll.wantsLayer=true;scroll.layer?.cornerRadius=10
        for (id,title,width) in [("title","Connector",335.0),("type","Connection",80.0),("installed","Registered",125.0)] {let col=NSTableColumn(identifier:NSUserInterfaceItemIdentifier(id));col.title=title;col.width=width;table.addTableColumn(col)}
        table.delegate=self;table.dataSource=self;table.rowHeight=58;table.intercellSpacing=NSSize(width:0,height:2);table.usesAlternatingRowBackgroundColors=false;table.style = .fullWidth;table.selectionHighlightStyle = .regular;table.backgroundColor = .white;scroll.documentView=table;addSubview(scroll)
        addSubview(Studio.line(NSRect(x:603,y:88,width:1,height:360)))
        detailLogo.frame=NSRect(x:628,y:390,width:50,height:50);detailLogo.imageScaling = .scaleProportionallyUpOrDown;addSubview(detailLogo);addSubview(inspectorTitle);addSubview(inspectorAuthor)
        let details=NSScrollView(frame:NSRect(x:628,y:190,width:335,height:165));details.hasVerticalScroller=true;details.drawsBackground=false;detail.frame=NSRect(x:0,y:0,width:315,height:360);detail.font = .systemFont(ofSize:13);details.documentView=detail;addSubview(details)
        desktop.frame=NSRect(x:628,y:155,width:335,height:26);desktop.state = .on;addSubview(desktop)
        code.frame=NSRect(x:628,y:125,width:335,height:26);code.state = .on;addSubview(code)
        button("Install",#selector(install),NSRect(x:624,y:82,width:105,height:34))
        button("Reinstall",#selector(reinstall),NSRect(x:733,y:82,width:105,height:34))
        button("Uninstall",#selector(uninstall),NSRect(x:842,y:82,width:122,height:34));buttons[1].bezelColor=Studio.navy;buttons[1].contentTintColor = .white;buttons[1].attributedTitle=NSAttributedString(string:"Install",attributes:[.foregroundColor:NSColor.white,.font:NSFont.systemFont(ofSize:13)]);buttons[3].contentTintColor = .systemRed
        button("Provider setup",#selector(setup),NSRect(x:624,y:43,width:166,height:30))
        button("CLI sign-in",#selector(signin),NSRect(x:798,y:43,width:166,height:30))
        button("Import bundle",#selector(importBundle),NSRect(x:624,y:6,width:166,height:30))
        button("Source details",#selector(sourceDetails),NSRect(x:798,y:6,width:166,height:30))
        status.frame=NSRect(x:22,y:51,width:560,height:25);status.font = .systemFont(ofSize:12);status.textColor=Studio.muted;addSubview(status)
        let note=NSTextField(wrappingLabelWithString:"Registered means configured, not connected. Sign-in status isn’t checked here. Model requests use your selected gateway.")
        note.frame=NSRect(x:22,y:6,width:560,height:38);note.font = .systemFont(ofSize:12);note.textColor=Studio.muted;addSubview(note)
        load(false)
    }
    required init?(coder:NSCoder){ fatalError() }
    func button(_ title:String,_ action:Selector,_ frame:NSRect) { let b=InkButton(title:title,target:self,action:action);b.primary=title=="Install";b.destructive=title=="Uninstall"; b.frame=frame; addSubview(b); buttons.append(b) }
    func run(_ args:[String]) throws -> [String:Any] {
        let p=Process(); p.executableURL=URL(fileURLWithPath:"/opt/homebrew/bin/python3"); var arguments=args;var input:Pipe?
        if arguments.first == "install-local" && arguments.count>3 {
            let payload=arguments[3];arguments[3]="-";let pipe=Pipe();p.standardInput=pipe;input=pipe
            p.arguments=[Bundle.main.resourceURL!.appendingPathComponent("catalog.py").path]+arguments
            let out=Pipe();p.standardOutput=out;p.standardError=FileHandle.nullDevice;try p.run()
            pipe.fileHandleForWriting.write(payload.data(using:.utf8)!);try pipe.fileHandleForWriting.close()
            let data=out.fileHandleForReading.readDataToEndOfFile();p.waitUntilExit()
            let v=try JSONSerialization.jsonObject(with:data) as! [String:Any]
            if v["ok"] as? Bool != true {throw NSError(domain:"Catalog",code:1,userInfo:[NSLocalizedDescriptionKey:v["error"] as? String ?? "Catalog error"])}
            return v
        }
        _ = input
        p.arguments=[Bundle.main.resourceURL!.appendingPathComponent("catalog.py").path]+arguments
        let out=Pipe(); p.standardOutput=out; p.standardError=FileHandle.nullDevice; try p.run(); let data=out.fileHandleForReading.readDataToEndOfFile(); p.waitUntilExit()
        let v=try JSONSerialization.jsonObject(with:data) as! [String:Any]
        if v["ok"] as? Bool != true { throw NSError(domain:"Catalog",code:1,userInfo:[NSLocalizedDescriptionKey:v["error"] as? String ?? "Catalog error"]) }; return v
    }
    func task(_ args:[String],_ done:@escaping ([String:Any])->Void) {
        buttons.forEach{$0.isEnabled=false}; status.stringValue="Working…"
        DispatchQueue.global().async {
            let result=Result {try self.run(args)}
            DispatchQueue.main.async {
                self.buttons.forEach{$0.isEnabled=true}; self.updateActions()
                switch result { case .success(let v): done(v)
                case .failure(let e): self.status.stringValue=e.localizedDescription; let a=NSAlert(); a.messageText="MCP operation could not finish"; a.informativeText=e.localizedDescription; a.runModal() }
            }
        }
    }
    func load(_ update:Bool) { task([update ? "refresh":"list"]) { v in
        self.entries=v["entries"] as? [[String:Any]] ?? []; self.applyFilter()
        self.status.stringValue="\(self.entries.count) MCPs · Updated \(String((v["updated"] as? String ?? "Bundled snapshot").prefix(10)))"
    } }
    @objc func refresh(){load(true)}
    @objc func filterChanged(){applyFilter()}
    func controlTextDidChange(_ obj:Notification){applyFilter()}
    func applyFilter(){
        let q=search.stringValue.lowercased(); let f=filter.indexOfSelectedItem
        filtered=entries.filter { e in
            let hay="\(e["title"] ?? "") \(e["author"] ?? "") \(e["categories"] ?? "")".lowercased()
            return (q.isEmpty || hay.contains(q)) && (f==0 || f==1 && e["type"] as? String == "remote" || f==2 && e["type"] as? String == "local" || f==3 && (e["desktopInstalled"] as? Bool == true || e["codeInstalled"] as? Bool == true))
        }.sorted{ ($0["title"] as? String ?? "").localizedCaseInsensitiveCompare($1["title"] as? String ?? "") == .orderedAscending }
        table.reloadData(); table.deselectAll(nil);detailLogo.image=nil;inspectorTitle.stringValue="Choose a connector";inspectorAuthor.stringValue="";updateActions(); detail.stringValue="\(filtered.count) matching MCPs. Select a connector."
    }
    func numberOfRows(in tableView:NSTableView)->Int{filtered.count}
    func tableView(_ tableView:NSTableView,objectValueFor column:NSTableColumn?,row:Int)->Any? {
        let e=filtered[row]
        switch column?.identifier.rawValue {case "title":return e["title"]; case "type":return e["type"]; default:
            let clients=[e["desktopInstalled"] as? Bool == true ? "Desktop":nil,e["codeInstalled"] as? Bool == true ? "CLI":nil].compactMap{$0}.joined(separator:", ")
            return clients
        }
    }
    func tableView(_ tableView:NSTableView,viewFor column:NSTableColumn?,row:Int)->NSView? {
        let e=filtered[row]
        if column?.identifier.rawValue == "title" {
            let cell=NSTableCellView(frame:NSRect(x:0,y:0,width:305,height:58))
            let logo=NSImageView(frame:NSRect(x:10,y:11,width:34,height:34));logo.image=LogoStore.shared.image(e) ?? NSImage(systemSymbolName:"puzzlepiece.extension",accessibilityDescription:nil);logo.imageScaling = .scaleProportionallyUpOrDown;cell.addSubview(logo)
            let name=Studio.text(e["title"] as? String ?? "Connector",NSRect(x:55,y:28,width:275,height:20),13,.medium);name.maximumNumberOfLines=1;name.lineBreakMode = .byTruncatingTail;cell.addSubview(name)
            let author=Studio.text(e["author"] as? String ?? "",NSRect(x:55,y:8,width:275,height:18),12,.regular,Studio.muted);author.maximumNumberOfLines=1;author.lineBreakMode = .byTruncatingTail;cell.addSubview(author);return cell
        }
        return Studio.text(self.tableView(tableView,objectValueFor:column,row:row) as? String ?? "",NSRect(x:6,y:18,width:(column?.width ?? 100)-10,height:22),12,.regular,Studio.muted)
    }
    func tableView(_ tableView:NSTableView,rowViewForRow row:Int)->NSTableRowView? {CatalogRow()}
    var selected:[String:Any]? {table.selectedRow>=0 && table.selectedRow<filtered.count ? filtered[table.selectedRow]:nil}
    func updateActions(){
        guard buttons.count == 8 else{return}
        let e=selected; let endpoint=(e?["serverUrl"] as? String)?.hasPrefix("https://") == true
        let recipe=e?["recipe"] as? Bool == true
        let local=e?["type"] as? String == "local"; let downloaded=e?["downloaded"] as? Bool == true
        buttons[1].title=local && !downloaded && !recipe ? "Get" : "Install"
        buttons[1].attributedTitle=NSAttributedString(string:buttons[1].title,attributes:[.foregroundColor:NSColor.white,.font:NSFont.systemFont(ofSize:13)])
        buttons[1].isEnabled=endpoint || local; buttons[2].isEnabled=endpoint || local && (downloaded || recipe)
        buttons[6].isEnabled=local && !recipe;buttons[7].isEnabled=local || e?["localAlternative"] != nil
        buttons[7].title=e?["localAlternative"] != nil ? "Local alternative" : "Source details"
        buttons[3].isEnabled=(endpoint || local) && (e?["desktopInstalled"] as? Bool == true || e?["codeInstalled"] as? Bool == true)
        buttons[4].title=e?["setupGuide"] != nil ? "Setup checklist" : "Provider setup"; buttons[4].isEnabled=e != nil; buttons[5].isEnabled = !local && e?["codeInstalled"] as? Bool == true
    }
    func tableViewSelectionDidChange(_ notification:Notification){
        updateActions()
        guard let e=selected else{return}
        inspectorTitle.stringValue=e["title"] as? String ?? "Connector";inspectorAuthor.stringValue=e["author"] as? String ?? ""
        detailLogo.image=LogoStore.shared.image(e) ?? NSImage(systemSymbolName:"puzzlepiece.extension",accessibilityDescription:nil)
        if e["recipe"] as? Bool == true {
            detail.stringValue="Microsoft 365 — Local (Softeria)\nIndependent publisher\n\nUses Microsoft Graph directly with device-code sign-in. No localhost OAuth callback.\n\nInstall adds a read-only configuration to Desktop’s local JSON and/or CLI user JSON. Node.js / npx required.\n\nThe client downloads and runs version 0.156.2 when connecting. Tenant approval may be required.\n\nGateway inference routing stays unchanged."
            trimInspectorHeading()
            return
        }
        if e["type"] as? String == "local" {
            detail.stringValue="\(e["title"] ?? "")\n\(e["author"] ?? "")\n\n\(e["oneLiner"] ?? "")\n\nLocal MCP package.\n\(e["downloaded"] as? Bool == true ? "Downloaded — ready to review installation." : "Click Get to locate and download a publisher bundle, then approve installation.")\n\nImport bundle accepts .mcpb/.dxt files. Source details shows published configurations.\n\nDesktop uses its local MCP config; CLI uses its user config. Gateway routing stays unchanged."
            trimInspectorHeading()
            return
        }
        let url=e["serverUrl"] as? String
        detail.stringValue="\(e["title"] ?? "")\n\(e["author"] ?? "")\n\n\(e["oneLiner"] ?? "")\n\n\((e["categories"] as? [String] ?? []).joined(separator:", "))\n\n\(url ?? "Provider setup / desktop extension required. No endpoint published.")\n\nDesktop installs into your gateway profile. Restart Claude, then authorize under Connectors. CLI: use CLI sign-in or /mcp.\n\n\(e["localAlternative"] != nil ? "Local authentication failed? Choose Local alternative for a separate local Microsoft 365 server." : "")"
        trimInspectorHeading()
        if let guide=e["setupGuide"] as? [String:Any] {
            detail.stringValue="SETUP REQUIREMENTS\n"+(guide["summary"] as? String ?? "")+"\n\nChoose Setup checklist for prerequisite steps and direct provider links.\n\n"+detail.stringValue
        } else {
            detail.stringValue += "\n\nProvider-specific prerequisites have not been reviewed yet. Open Provider setup before connecting."
        }
    }
    func trimInspectorHeading(){detail.stringValue=detail.stringValue.components(separatedBy:"\n").dropFirst(2).joined(separator:"\n").trimmingCharacters(in:.whitespacesAndNewlines)}
    func change(_ action:String){
        guard let e=selected, let id=e["_id"] as? String else{return}
        var targets=[String](); if desktop.state == .on {targets.append("desktop")}; if code.state == .on {targets.append("code")}; if targets.isEmpty{return}
        task([action,id]+targets){v in ClientReload.offer(targets.filter{$0=="desktop"},message:"MCP registration updated. Authorization is separate; use your client to connect. Start a new Claude Code session for CLI changes."); self.load(false)}
    }
    @objc func install(){
        if selected?["recipe"] as? Bool == true {
            let a=NSAlert();a.messageText="Configure local Microsoft 365?";a.informativeText="This adds Softeria’s read-only MCP to the selected clients. On connection, npx downloads and runs version 0.156.2. Microsoft sign-in and tenant consent remain separate. Gateway routing stays unchanged.";a.addButton(withTitle:"Install");a.addButton(withTitle:"Cancel")
            if a.runModal() == .alertFirstButtonReturn {change("install")}
        } else if selected?["type"] as? String == "local" {
            if selected?["downloaded"] as? Bool == true,let id=selected?["_id"] as? String {let t=targets();task(["inspect",id]){self.reviewPackage($0,targets:t)}} else {getLocal()}
        } else {
            if let e=selected,let guide=e["setupGuide"] as? [String:Any],guide["requiresCredentials"] as? Bool == true {
                setup()
                let alert=NSAlert();alert.messageText="Register endpoint only?"
                alert.informativeText="This does not configure OAuth credentials. Complete the provider checklist and configure a compatible OAuth client or local bridge before connecting. A URL-only registration may still produce an authentication error."
                alert.addButton(withTitle:"Register endpoint");alert.addButton(withTitle:"Cancel")
                guard alert.runModal() == .alertFirstButtonReturn else{return}
            }
            change("install")
        }
    }; @objc func reinstall(){install()}; @objc func uninstall(){change("uninstall")}
    @objc func setup(){
        guard let e=selected else{return}
        if let guide=e["setupGuide"] as? [String:Any] {
            ProviderSetupPanel(guide,endpoint:e["serverUrl"] as? String ?? "").show(title:e["title"] as? String ?? "Connector")
        } else if let s=e["directoryUrl"] as? String,let u=URL(string:s) {NSWorkspace.shared.open(u)}
    }
    func targets() -> [String] {
        var t=[String](); if desktop.state == .on {t.append("desktop")}; if code.state == .on {t.append("code")}; return t
    }
    @objc func importBundle(){
        guard let e=selected,let id=e["_id"] as? String else{return}
        let panel=NSOpenPanel();panel.allowedContentTypes=[UTType(filenameExtension:"mcpb") ?? .data, UTType(filenameExtension:"dxt") ?? .data];panel.allowsMultipleSelection=false;panel.canChooseDirectories=false
        if panel.runModal() == .OK, let url=panel.url { task(["import",id,url.path]){self.reviewPackage($0,targets:self.targets())} }
    }
    @objc func sourceDetails(){
        if let alternative=selected?["localAlternative"] as? String {
            filter.selectItem(at:0);search.stringValue="Microsoft 365";applyFilter()
            if let row=filtered.firstIndex(where:{$0["_id"] as? String == alternative}) {table.selectRowIndexes(IndexSet(integer:row),byExtendingSelection:false)}
            return
        }
        if selected?["recipe"] as? Bool == true {setup();return}
        guard let id=selected?["_id"] as? String else{return}
        task(["resolve",id]){v in
            let sources=(v["sources"] as? [String] ?? []).joined(separator:"\n")
            let configs=(v["configurations"] as? [String] ?? []).joined(separator:"\n\n")
            let packages=(v["packages"] as? [[String:Any]] ?? []).compactMap{$0["url"] as? String}.joined(separator:"\n")
            let a=NSAlert();a.messageText="Publisher sources and local configurations"
            a.informativeText="Published examples are reference material. The downloaded bundle manifest determines what this app installs."
            a.accessoryView=self.textPanel("\(sources)\n\nPackages:\n\(packages)\n\nConfigurations:\n\(configs)\n\n\(v["note"] ?? "")")
            a.runModal();self.status.stringValue="Publisher sources checked."
        }
    }
    func textPanel(_ text:String) -> NSScrollView {
        let scroll=NSScrollView(frame:NSRect(x:0,y:0,width:560,height:260));scroll.hasVerticalScroller=true
        let view=NSTextView(frame:scroll.bounds);view.isEditable=false;view.isSelectable=true;view.font = .monospacedSystemFont(ofSize:11,weight:.regular);view.string=text;view.isVerticallyResizable=true;view.autoresizingMask=[.width];scroll.documentView=view;return scroll
    }
    func getLocal(){
        guard let e=selected, let id=e["_id"] as? String else{return}
        let selectedTargets=targets()
        task(["resolve-refresh",id]){v in
            let packages=v["packages"] as? [[String:Any]] ?? []
            var url:String?
            if packages.count==1 {url=packages[0]["url"] as? String}
            else if packages.count>1 {
                let a=NSAlert();a.messageText="Choose a publisher package"
                a.informativeText="Choose the macOS package you want to download. Installation is a separate confirmation."
                let picker=NSPopUpButton(frame:NSRect(x:0,y:0,width:500,height:30));picker.addItems(withTitles:packages.map{$0["name"] as? String ?? "Package"});a.accessoryView=picker
                a.addButton(withTitle:"Download");a.addButton(withTitle:"Cancel")
                if a.runModal() == .alertFirstButtonReturn {url=packages[picker.indexOfSelectedItem]["url"] as? String}
            } else {
                let a=NSAlert();a.messageText="A public bundle URL is needed"
                a.informativeText="No public Mac bundle was located for this entry. Paste an official HTTPS .mcpb URL, or cancel and use Import bundle for a file downloaded through Claude's signed-in directory."
                let input=NSTextField(frame:NSRect(x:0,y:0,width:500,height:28));input.placeholderString="https://publisher.example/extension.mcpb";a.accessoryView=input
                a.addButton(withTitle:"Download");a.addButton(withTitle:"Cancel");a.addButton(withTitle:"Publisher page")
                let response=a.runModal()
                if response == .alertFirstButtonReturn, !input.stringValue.isEmpty {url=input.stringValue}
                if response == .alertThirdButtonReturn,let link=v["repository"] as? String ?? v["directoryUrl"] as? String,let page=URL(string:link){NSWorkspace.shared.open(page)}
            }
            guard let download=url else{self.status.stringValue="No package downloaded.";return}
            self.task(["get",id,download]){self.reviewPackage($0,targets:selectedTargets)}
        }
    }
    func reviewPackage(_ info:[String:Any],targets:[String]) {
        guard let id=info["id"] as? String,let hash=info["sha256"] as? String,let manifest=info["manifest"] as? [String:Any] else{return}
        if targets.isEmpty { status.stringValue="Package downloaded. Select Desktop and/or CLI before installing.";load(false);return }
        let a=NSAlert();a.messageText="Package downloaded — install it?"
        a.informativeText="Installation adds a local program to the selected Claude clients. It can run when those clients connect. This app has not verified the publisher signature."
        let command="\(info["command"] ?? "") \((info["args"] as? [String] ?? []).joined(separator:" "))"
        a.accessoryView=textPanel("\(manifest["display_name"] ?? manifest["name"] ?? "Extension")\nVersion: \(info["version"] ?? "")\nSource: \(info["source"] ?? "")\nSHA-256: \(hash)\nTargets: \(targets.joined(separator:", "))\n\nLaunch command:\n\(command)\n\nTools:\n\((info["tools"] as? [String] ?? []).joined(separator:"\n"))\n\nSettings:\n\((info["userConfig"] as? [String:Any] ?? [:]).keys.sorted().joined(separator:", "))")
        a.addButton(withTitle:"Keep download");a.addButton(withTitle:"Install")
        guard a.runModal() == .alertSecondButtonReturn else {load(false);return}
        var values=[String:Any]()
        for (key,raw) in (info["userConfig"] as? [String:Any] ?? [:]).sorted(by:{$0.key<$1.key}) {
            guard let field=raw as? [String:Any] else{continue}
            let prompt=NSAlert();prompt.messageText=field["title"] as? String ?? key
            let multiple=field["multiple"] as? Bool == true;let type=field["type"] as? String ?? "string"
            prompt.informativeText=(field["description"] as? String ?? "") + (multiple ? "\nEnter a JSON array, for example [\"/Users/you/Documents\"].":"") + (type=="boolean" ? "\nEnter true or false.":"")
            let input:NSTextField = field["sensitive"] as? Bool == true ? NSSecureTextField(frame:NSRect(x:0,y:0,width:480,height:28)):NSTextField(frame:NSRect(x:0,y:0,width:480,height:28))
            if let value=field["default"] {
                if let s=value as? String {input.stringValue=s}
                else if let data=try? JSONSerialization.data(withJSONObject:value,options:[.fragmentsAllowed]),let s=String(data:data,encoding:.utf8){input.stringValue=s}
            }
            prompt.accessoryView=input;prompt.addButton(withTitle:"Continue");prompt.addButton(withTitle:"Cancel")
            if prompt.runModal() != .alertFirstButtonReturn {load(false);return}
            if multiple || type=="boolean" || type=="number" {
                guard let data=input.stringValue.data(using:.utf8),let parsed=try? JSONSerialization.jsonObject(with:data,options:[.fragmentsAllowed]) else{status.stringValue="Invalid setting format; package kept for another installation attempt.";return}
                values[key]=parsed
            } else {values[key]=input.stringValue}
        }
        do {
            let data=try JSONSerialization.data(withJSONObject:values);let json=String(data:data,encoding:.utf8)!
            task(["install-local",id,hash,json]+targets){v in ClientReload.offer(targets.filter{$0=="desktop"},message:v["message"] as? String ?? "Local MCP configured.");self.load(false)}
        } catch {status.stringValue=error.localizedDescription}
    }

    @objc func signin(){
        guard let e=selected, e["codeInstalled"] as? Bool == true,let slug=e["slug"] as? String else {status.stringValue="Install for Claude Code first, then choose CLI sign-in.";return}
        let name="catalog-"+slug.lowercased().replacingOccurrences(of:"[^a-z0-9-]",with:"-",options:.regularExpression)
        let path=FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/AI Control Studio/MCP sign-in.command")
        do { try "#!/bin/zsh\n\"$HOME/.local/bin/claude\" mcp login '\(name)'\n".write(to:path,atomically:true,encoding:.utf8); try FileManager.default.setAttributes([.posixPermissions:0o700],ofItemAtPath:path.path); NSWorkspace.shared.open(path) } catch {status.stringValue=error.localizedDescription}
    }
}
