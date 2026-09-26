import AppKit

/// Provider guidance is reviewed reference material, not a test of OAuth readiness.
final class ProviderSetupPanel: NSObject {
    private let guide: [String:Any]
    private let key: String
    private var steps: [[String:Any]] { guide["steps"] as? [[String:Any]] ?? [] }
    init(_ guide:[String:Any], endpoint:String) {self.guide=guide;self.key="setup-checklist:"+endpoint}
    func show(title:String) {
        let alert=NSAlert();alert.icon=NSApp.applicationIconImage;alert.messageText="Set up \(title)"
        alert.informativeText="\(guide["summary"] as? String ?? "")\n\nChecked steps are your notes, not verified authentication. Reviewed \(guide["reviewed"] as? String ?? "unknown date")."
        let scroll=NSScrollView(frame:NSRect(x:0,y:0,width:610,height:340));scroll.hasVerticalScroller=true;scroll.drawsBackground=false
        let view=NSView(frame:NSRect(x:0,y:0,width:588,height:CGFloat(steps.count)*125));scroll.documentView=view
        let saved=UserDefaults.standard.array(forKey:key) as? [Int] ?? []
        for (i,step) in steps.enumerated() {
            let y=CGFloat(steps.count-i-1)*125
            let check=NSButton(checkboxWithTitle:"\(i+1). \(step["title"] as? String ?? "Step")",target:self,action:#selector(toggle(_:)))
            check.frame=NSRect(x:0,y:y+92,width:570,height:26);check.tag=i;check.state=saved.contains(i) ? .on:.off;view.addSubview(check)
            let text=NSTextField(wrappingLabelWithString:step["description"] as? String ?? "")
            text.frame=NSRect(x:22,y:y+34,width:540,height:56);text.font = .systemFont(ofSize:12);view.addSubview(text)
            let open=NSButton(title:"Open this step ↗",target:self,action:#selector(openStep(_:)));open.bezelStyle = .rounded
            open.frame=NSRect(x:20,y:y+3,width:180,height:28);open.tag=i;view.addSubview(open)
        }
        alert.accessoryView=scroll;scroll.contentView.scroll(to:NSPoint(x:0,y:max(0,view.frame.height-scroll.contentView.bounds.height)));scroll.reflectScrolledClipView(scroll.contentView);alert.addButton(withTitle:"Done");alert.runModal()
    }
    @objc private func toggle(_ sender:NSButton) {
        var saved=Set(UserDefaults.standard.array(forKey:key) as? [Int] ?? [])
        if sender.state == .on {saved.insert(sender.tag)} else {saved.remove(sender.tag)}
        UserDefaults.standard.set(Array(saved).sorted(),forKey:key)
    }
    @objc private func openStep(_ sender:NSButton) {
        guard sender.tag<steps.count,let s=steps[sender.tag]["url"] as? String,let u=URL(string:s),u.scheme=="https" else{return}
        NSWorkspace.shared.open(u)
    }
}

/// Uses normal quit requests so the target can present its own unsaved-work prompts.
enum ClientReload {
    static func offer(_ targets:[String], message:String) {
        let ids=targets.map { $0=="desktop" ? "com.anthropic.claudefordesktop" : "com.openai.codex" }
        let running=NSWorkspace.shared.runningApplications.filter {ids.contains($0.bundleIdentifier ?? "") && $0.processIdentifier != ProcessInfo.processInfo.processIdentifier}
        let alert=NSAlert();alert.messageText="Configuration saved"
        alert.informativeText=message + (running.isEmpty ? "\n\nNo affected desktop app is running. Changes will load next time you open it." : "\n\nChoose which running apps to quit and reopen. Finish active work first; each app can ask you to save. CLI sessions must be started again separately.")
        if running.isEmpty {alert.addButton(withTitle:"OK");alert.runModal();return}
        let view=NSView(frame:NSRect(x:0,y:0,width:420,height:CGFloat(running.count)*30))
        var checks=[NSButton]()
        for (i,app) in running.enumerated() {
            let c=NSButton(checkboxWithTitle:app.localizedName ?? "Client",target:nil,action:nil);c.state = .on
            c.frame=NSRect(x:0,y:CGFloat(running.count-i-1)*30,width:420,height:28);view.addSubview(c);checks.append(c)
        }
        alert.accessoryView=view;alert.addButton(withTitle:"Quit & reopen selected");alert.addButton(withTitle:"Later")
        guard alert.runModal() == .alertFirstButtonReturn else{return}
        for (i,app) in running.enumerated() where checks[i].state == .on {
            guard let url=app.bundleURL else{continue}
            if !app.terminate() {report("\(app.localizedName ?? "App") did not accept the quit request. Its configuration is saved; reopen it when ready.");continue}
            waitForExit(app,url:url,deadline:Date().addingTimeInterval(60))
        }
    }
    private static func waitForExit(_ app:NSRunningApplication,url:URL,deadline:Date) {
        if app.isTerminated {
            NSWorkspace.shared.openApplication(at:url,configuration:NSWorkspace.OpenConfiguration()) {_,error in
                if let error=error {DispatchQueue.main.async {report("Could not reopen \(app.localizedName ?? "app"): \(error.localizedDescription)")}}
            }
        } else if Date()>deadline {report("\(app.localizedName ?? "App") is still open. Complete any save or quit prompts, then reopen it manually. It was not force-quit.")}
        else {DispatchQueue.main.asyncAfter(deadline:.now()+0.5) {waitForExit(app,url:url,deadline:deadline)}}
    }
    private static func report(_ text:String) {let alert=NSAlert();alert.messageText="App reload needs attention";alert.informativeText=text;alert.runModal()}
}
