import AppKit
import WebKit

final class ConfigurationStudioView:NSView,WKScriptMessageHandler,WKNavigationDelegate,WKUIDelegate {
    private var web:WKWebView!
    private let mode:String
    init(frame:NSRect,mode:String) {
        self.mode=mode;super.init(frame:frame)
        let config=WKWebViewConfiguration();config.userContentController.add(self,name:"studio")
        web=WKWebView(frame:bounds,configuration:config);web.autoresizingMask=[.width,.height];web.navigationDelegate=self;web.uiDelegate=self;addSubview(web)
        if let url=Bundle.main.url(forResource:"studio",withExtension:"html") {web.loadFileURL(url,allowingReadAccessTo:url.deletingLastPathComponent())}
    }
    required init?(coder:NSCoder){fatalError()}
    func webView(_ webView:WKWebView,runJavaScriptConfirmPanelWithMessage message:String,initiatedByFrame frame:WKFrameInfo,completionHandler:@escaping(Bool)->Void) {
        let alert=NSAlert();alert.messageText=message;alert.addButton(withTitle:message.hasPrefix("Send each") ? "Enable":"Discard");alert.addButton(withTitle:message.hasPrefix("Send each") ? "Cancel":"Keep editing")
        completionHandler(alert.runModal() == .alertFirstButtonReturn)
    }
    func webView(_ webView:WKWebView,didFinish navigation:WKNavigation!) {web.evaluateJavaScript("start(\(String(data:try! JSONSerialization.data(withJSONObject:mode,options:.fragmentsAllowed),encoding:.utf8)!))")}
    func webView(_ webView:WKWebView,decidePolicyFor navigationAction:WKNavigationAction,decisionHandler:@escaping(WKNavigationActionPolicy)->Void) {
        if let u=navigationAction.request.url,u.scheme=="https" {NSWorkspace.shared.open(u);decisionHandler(.cancel)} else {decisionHandler(navigationAction.request.url?.isFileURL == true ? .allow:.cancel)}
    }
    func userContentController(_ userContentController:WKUserContentController,didReceive message:WKScriptMessage) {
        guard var request=message.body as? [String:Any],let id=request.removeValue(forKey:"requestId") else{return}
        if request["op"] as? String == "copy",let text=request["text"] as? String {
            NSPasteboard.general.clearContents();NSPasteboard.general.setString(text,forType:.string);reply(id,["ok":true]);return
        }
        if request["op"] as? String == "choose-project" {
            let panel=NSOpenPanel();panel.canChooseDirectories=true;panel.canChooseFiles=false
            reply(id,["ok":true,"project":panel.runModal() == .OK ? panel.url?.path ?? "":""]);return
        }
        if request["op"] as? String == "reveal",let path=request["path"] as? String {NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath:path)]);reply(id,["ok":true]);return}
        let op=request["op"] as? String ?? ""
        if op.hasPrefix("secret-") {
            do {
                let result:[String:Any]
                if op=="secret-list" {result=try SecretVault.list()}
                else if op=="secret-edit" {result=try SecretVault.edit(request["id"] as? String)}
                else if op=="secret-remove",let ident=request["id"] as? String {result=try SecretVault.remove(ident)}
                else {throw SecretVault.failure("Unknown secret action.")}
                reply(id,result)
            } catch {reply(id,["ok":false,"error":error.localizedDescription])}
            return
        }
        if op=="skill-import" {
            let alert=NSAlert();alert.messageText="Import this skill into Claude Code?"
            alert.informativeText="The downloaded instructions and supporting files will become available to Claude Code. Skills can contain scripts and tool permissions. Review their files before importing. The importer does not execute them."
            alert.addButton(withTitle:"Import");alert.addButton(withTitle:"Cancel")
            guard alert.runModal() == .alertFirstButtonReturn else{reply(id,["ok":false,"error":"Import cancelled."]);return}
        }
        if op=="hook-save" || op=="hooks-edit" || op=="plugin-install" || op=="plugin-toggle" {
            let a=NSAlert();a.messageText=op.hasPrefix("hook") ? "Save executable hook configuration?":"Change Claude Code plugin configuration?"
            a.informativeText=op.hasPrefix("hook") ? "Claude Code will run these hooks or send event data to the configured HTTP endpoint when the selected event occurs. Review the target before saving.":"This changes your Claude Code configuration. Installed plugins can supply tools, instructions and hooks. Start a new CLI session to load the change."
            a.addButton(withTitle:"Apply");a.addButton(withTitle:"Cancel")
            guard a.runModal() == .alertFirstButtonReturn else{reply(id,["ok":false,"error":"Cancelled; configuration kept."]);return}
        }
        let payload=request
        DispatchQueue.global().async {
            do {
                let process=Process();process.executableURL=URL(fileURLWithPath:Bundle.main.object(forInfoDictionaryKey:"AIControlPythonRuntime") as? String ?? "/usr/bin/python3")
                let script=op.hasPrefix("profile") ? "gateway_profiles.py":"studio.py"
                process.arguments=[Bundle.main.resourceURL!.appendingPathComponent(script).path]
                let input=Pipe(),output=Pipe();process.standardInput=input;process.standardOutput=output;process.standardError=FileHandle.nullDevice
                try process.run();input.fileHandleForWriting.write(try JSONSerialization.data(withJSONObject:payload));try input.fileHandleForWriting.close()
                let data=output.fileHandleForReading.readDataToEndOfFile();process.waitUntilExit()
                let result=try JSONSerialization.jsonObject(with:data) as! [String:Any]
                DispatchQueue.main.async {self.reply(id,result);if (op=="profile-save" || op=="profile-select"),result["ok"] as? Bool == true,result["applied"] is [String:Any] {ClientReload.offer(result["reloadTargets"] as? [String] ?? [],message:"Gateway profile applied to enabled clients. Start a new Claude Code terminal/session if its route changed.")};if op=="jev-save",result["ok"] as? Bool == true {ClientReload.offer(["desktop"],message:"Jev settings saved. Start a new Claude Code session to load its MCP and guidance hook.")}}
            } catch {DispatchQueue.main.async {self.reply(id,["ok":false,"error":error.localizedDescription])}}
        }
    }
    private func reply(_ id:Any,_ result:[String:Any]) {
        let data=try! JSONSerialization.data(withJSONObject:["id":id,"result":result]);let json=String(data:data,encoding:.utf8)!
        web.evaluateJavaScript("receive(\(json))")
    }
}
