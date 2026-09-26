import AppKit
import Foundation

final class SwitchApp: NSObject, NSApplicationDelegate {
    private var window: NSWindow!
    private var desktopBox: WorkshopSwitch!
    private var codeBox: WorkshopSwitch!
    private var codexBox: WorkshopSwitch!
    private var codexModel: NSComboBox!
    private var codexWasOn = false
    private var navigation: NSTabView!
    private var navButtons: [NSButton] = []
    private var statusLabel: NSTextField!

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        buildMenus()
        if let url=Bundle.main.url(forResource:"pixel-switch-icon",withExtension:"png"){NSApp.applicationIconImage=NSImage(contentsOf:url)}
        buildWindow()
        refreshStatus()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func buildMenus() {
        let main = NSMenu()
        let appItem = NSMenuItem()
        main.addItem(appItem)
        let applicationMenu = NSMenu(title: "AI Control Studio")
        applicationMenu.addItem(withTitle: "Quit AI Control Studio", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = applicationMenu

        let editItem = NSMenuItem()
        main.addItem(editItem)
        let editMenu = NSMenu(title: "Edit")
        // Nil targets dispatch to the focused native field or WebKit editor.
        for (title, selector, key, modifiers) in [
            ("Undo", "undo:", "z", NSEvent.ModifierFlags.command),
            ("Redo", "redo:", "z", NSEvent.ModifierFlags([.command, .shift])),
            ("Cut", "cut:", "x", NSEvent.ModifierFlags.command),
            ("Copy", "copy:", "c", NSEvent.ModifierFlags.command),
            ("Paste", "paste:", "v", NSEvent.ModifierFlags.command),
            ("Select All", "selectAll:", "a", NSEvent.ModifierFlags.command)
        ] {
            let item = NSMenuItem(title: title, action: NSSelectorFromString(selector), keyEquivalent: key)
            item.keyEquivalentModifierMask = modifiers
            editMenu.addItem(item)
        }
        editItem.submenu = editMenu
        NSApp.mainMenu = main
    }

    private func label(_ text: String, frame: NSRect, size: CGFloat, bold: Bool = false,
                       color: NSColor = .labelColor) -> NSTextField {
        let field = NSTextField(labelWithString: text)
        field.frame = frame
        field.font = bold ? .boldSystemFont(ofSize: size) : .systemFont(ofSize: size)
        field.textColor = color
        field.lineBreakMode = .byWordWrapping
        field.maximumNumberOfLines = 0
        return field
    }

    private func buildWindow() {
        let shell=PaperView(frame:NSRect(x:0,y:0,width:1320,height:740))
        window=NSWindow(contentRect:shell.frame,styleMask:[.titled,.closable,.miniaturizable,.fullSizeContentView],backing:.buffered,defer:false)
        window.title="AI Control Studio";window.titleVisibility = .hidden;window.titlebarAppearsTransparent=true;window.titlebarSeparatorStyle = .none;window.isMovableByWindowBackground=true;window.contentView=shell;window.isReleasedWhenClosed=false
        window.appearance=NSAppearance(named:.aqua);window.center()
        let sidebar=PaperView(frame:NSRect(x:0,y:0,width:240,height:740));shell.addSubview(sidebar)
        if let url=Bundle.main.url(forResource:"pixel-switch-icon",withExtension:"png"),let image=NSImage(contentsOf:url){_ = image;sidebar.addSubview(Studio.artwork("pixel-switch-sidebar",NSRect(x:27,y:632,width:86,height:86)))}
        sidebar.addSubview(Studio.text("Control Studio",NSRect(x:23,y:601,width:200,height:30),20,.semibold,Studio.navy))
        sidebar.addSubview(Studio.text("AI models & tools",NSRect(x:23,y:578,width:155,height:22),12,.regular,Studio.muted))
        for (index,title,symbol) in [(0,"Connections","switch.2"),(1,"MCP Catalog","puzzlepiece.extension"),(2,"Code Studio","square.and.pencil"),(3,"Gateway profiles","network"),(4,"Mods","slider.horizontal.3"),(5,"Secret Manager","key.fill")] {
            let b=SidebarButton(title:title,target:self,action:#selector(navigate));b.tag=index;b.frame=NSRect(x:18,y:506-CGFloat(index)*68,width:204,height:54);b.bezelStyle = .inline;b.setButtonType(.toggle);b.isBordered=false;b.wantsLayer=true;b.state=index==0 ? .on:.off;b.setAccessibilityValue(index==0 ? "Selected":"");b.image=NSImage(systemSymbolName:symbol,accessibilityDescription:nil);b.imagePosition = .imageLeading;b.alignment = .left;b.contentTintColor=Studio.navy;sidebar.addSubview(b);navButtons.append(b)
        }
        sidebar.addSubview(Studio.text("Local configuration\nYour existing sign-in",NSRect(x:23,y:25,width:155,height:45),12,.regular,Studio.muted))
        shell.addSubview(Studio.text("AI Control Studio",NSRect(x:275,y:686,width:420,height:30),22,.semibold,Studio.navy))
        shell.addSubview(Studio.text("ROUTE MODELS · YOUR TOOLS · YOUR CHOICE",NSRect(x:275,y:660,width:450,height:18),10,.medium,Studio.muted))

        
        let tabs=NSTabView(frame:NSRect(x:260,y:10,width:1050,height:650));tabs.tabViewType = .noTabsNoBorder;navigation=tabs
        tabs.font = .systemFont(ofSize:14,weight:.medium)
        let content=PaperView(frame:NSRect(x:0,y:0,width:1080,height:600))
        let gateway=NSTabViewItem(identifier:"gateway");gateway.label="Connections";gateway.view=content;tabs.addTabViewItem(gateway)
        let catalog=NSTabViewItem(identifier:"catalog");catalog.label="MCP Catalog";catalog.view=CatalogView(frame:NSRect(x:0,y:0,width:1080,height:600));tabs.addTabViewItem(catalog)
        for (id,title,mode) in [("studio","Code Studio","studio"),("profiles","Gateway profiles","profiles"),("mods","Mods","mods"),("secrets","Secret Manager","secrets")] {
            let tab=NSTabViewItem(identifier:id);tab.label=title;tab.view=ConfigurationStudioView(frame:NSRect(x:0,y:0,width:1050,height:600),mode:mode);tabs.addTabViewItem(tab)
        }
        shell.addSubview(tabs)
        shell.addSubview(Studio.line(NSRect(x:270,y:648,width:700,height:1)))
        shell.addSubview(Studio.line(NSRect(x:239,y:0,width:1,height:740)))
        shell.addSubview(Studio.artwork("workshop-header",NSRect(x:990,y:572,width:280,height:146)))
        content.addSubview(Studio.text("Choose your connection",NSRect(x:32,y:515,width:620,height:44),30,.semibold,Studio.navy))
        content.addSubview(Studio.text("Switch each client independently. Apply when you’re ready.",NSRect(x:32,y:480,width:660,height:26),14,.regular,Studio.muted))
        let rows:[(String,String,String,CGFloat)] = [
            ("workshop-desktop","Claude Desktop","Off returns to direct Claude sign-in after restarting.",395),
            ("workshop-code","Claude Code","Off returns the terminal client to its normal sign-in.",295),
            ("workshop-codex","Codex Desktop + CLI","Uses the selected gateway credentials. Off restores your previous settings.",195)]
        for row in rows {
            content.addSubview(Studio.artwork(row.0,NSRect(x:25,y:row.3-7,width:70,height:70)))
            content.addSubview(Studio.text(row.1,NSRect(x:112,y:row.3+17,width:550,height:27),18,.semibold))
            content.addSubview(Studio.text(row.2,NSRect(x:112,y:row.3-8,width:620,height:24),12,.regular,Studio.muted))
            content.addSubview(Studio.line(NSRect(x:32,y:row.3-32,width:940,height:1)))
        }
        desktopBox=WorkshopSwitch(frame:NSRect(x:920,y:402,width:62,height:32));desktopBox.target=self;desktopBox.action=#selector(markPending);content.addSubview(desktopBox);content.addSubview(Studio.text("Proxy",NSRect(x:871,y:405,width:40,height:22),12,.medium,Studio.navy))
        codeBox=WorkshopSwitch(frame:NSRect(x:920,y:302,width:62,height:32));codeBox.target=self;codeBox.action=#selector(markPending);content.addSubview(codeBox);content.addSubview(Studio.text("Proxy",NSRect(x:871,y:305,width:40,height:22),12,.medium,Studio.navy))
        codexBox=WorkshopSwitch(frame:NSRect(x:920,y:202,width:62,height:32));codexBox.target=self;codexBox.action=#selector(markPending);content.addSubview(codexBox);content.addSubview(Studio.text("Proxy",NSRect(x:871,y:205,width:40,height:22),12,.medium,Studio.navy))
        desktopBox.setAccessibilityLabel("Claude Desktop through selected gateway");codeBox.setAccessibilityLabel("Claude Code through selected gateway");codexBox.setAccessibilityLabel("Codex through selected gateway")
        codexModel=NSComboBox(frame:NSRect(x:84,y:120,width:400,height:30));codexModel.placeholderString="Choose an allowed Codex model";content.addSubview(codexModel)
        let models=InkButton(title:"Load gateway models",target:self,action:#selector(loadCodexModels));models.frame=NSRect(x:495,y:117,width:165,height:34);content.addSubview(models)
        content.addSubview(Studio.text("ChatGPT · Custom gateway routing is unavailable.",NSRect(x:84,y:83,width:640,height:22),12,.regular,Studio.muted))
        statusLabel=Studio.text("Checking settings…",NSRect(x:32,y:27,width:655,height:32),12,.regular,Studio.muted);content.addSubview(statusLabel)
        let apply=InkButton(title:"Apply changes",target:self,action:#selector(applySelection));apply.frame=NSRect(x:825,y:20,width:150,height:38);apply.primary=true;apply.keyEquivalent="\r";apply.bezelStyle = .rounded;apply.contentTintColor=Studio.navy;content.addSubview(apply)
    }

    @objc private func navigate(_ sender:NSButton){if sender.tag==0 {refreshStatus()};navigation.selectTabViewItem(at:sender.tag);for b in navButtons {let selected=b.tag==sender.tag;b.state=selected ? .on:.off;b.needsDisplay=true;b.setAccessibilityValue(selected ? "Selected":"")}}
    @objc private func markPending(){statusLabel.stringValue="Changes pending · Click Apply changes to save."}
    private func backend(_ arguments: [String], scriptName: String = "switch.py") throws -> [String: Any] {
        guard let script = Bundle.main.resourceURL?.appendingPathComponent(scriptName) else {
            throw NSError(domain: "AI Control Studio", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "Missing switch.py in the app bundle"])
        }
        let process = Process()
        process.executableURL = URL(fileURLWithPath: Bundle.main.object(forInfoDictionaryKey:"AIControlPythonRuntime") as? String ?? "/usr/bin/python3")
        process.arguments = [script.path] + arguments
        let output = Pipe()
        process.standardOutput = output
        process.standardError = Pipe()
        try process.run()
        let data = output.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()
        guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw NSError(domain: "AI Control Studio", code: 2,
                          userInfo: [NSLocalizedDescriptionKey: "Could not read the switch result"])
        }
        if (object["ok"] as? Bool) != true {
            let message = object["error"] as? String ?? "Unknown error"
            throw NSError(domain: "AI Control Studio", code: 3,
                          userInfo: [NSLocalizedDescriptionKey: message])
        }
        return object
    }

    private func showError(_ error: Error) {
        let alert = NSAlert()
        alert.alertStyle = .warning
        alert.messageText = "Could not change gateway settings"
        alert.informativeText = error.localizedDescription
        alert.runModal()
    }

    private func updateStatus(_ state: [String: Any]) {
        let desktop = (state["desktop_gateway"] as? Bool) == true
        let code = (state["code_gateway"] as? Bool) == true
        desktopBox.state = desktop ? .on : .off
        codeBox.state = code ? .on : .off
        let name=state["gateway_name"] as? String ?? "Gateway"
        statusLabel.stringValue = "Selected: \(name) · Desktop \(desktop ? "proxy" : "direct") · Code \(code ? "proxy" : "direct") · Codex \(codexWasOn ? "proxy" : "previous provider")"
    }

    private func refreshStatus() {
        do { let routingState=try backend(["status"])
            let state=try backend(["status"],scriptName:"codex_switch.py");codexWasOn=state["codex_gateway"] as? Bool == true;codexBox.state=codexWasOn ? .on : .off
            if codexWasOn {codexModel.stringValue=state["codex_model"] as? String ?? ""}
            updateStatus(routingState)
        }
        catch { showError(error) }
    }

    @objc private func loadCodexModels() {
        DispatchQueue.global().async {
            let result=Result {try self.backend(["models"],scriptName:"codex_switch.py")}
            DispatchQueue.main.async {switch result {case .success(let v):self.codexModel.removeAllItems();self.codexModel.addItems(withObjectValues:v["models"] as? [String] ?? []);if self.codexModel.stringValue.isEmpty {self.codexModel.selectItem(at:0)}
            case .failure(let e):self.showError(e)}}
        }
    }
    @objc private func applySelection() {
        do {
            let wantCodex=codexBox.state == .on
            let result=try backend([desktopBox.state == .on ? "on":"off",codeBox.state == .on ? "on":"off",wantCodex ? "on":"off",codexModel.stringValue],scriptName:"apply_bundle.py")
            codexWasOn=result["codex_gateway"] as? Bool == true
            updateStatus(result)
            let desktopRestart = (result["desktop_restart_needed"] as? Bool) == true
            let newTerminal = (result["code_new_terminal_needed"] as? Bool) == true
            var reloadTargets=[String]()
            if desktopRestart {reloadTargets.append("desktop")}
            if result["codex_restart_needed"] as? Bool == true {reloadTargets.append("codex")}
            ClientReload.offer(reloadTargets,message:"Gateway choices saved."+(newTerminal ? "\nStart a new terminal/session for Claude Code changes." : ""))
        } catch {
            showError(error)
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    @objc private func closeWindow() {
        NSApp.terminate(nil)
    }
}

let app = NSApplication.shared
let delegate = SwitchApp()
app.delegate = delegate
app.run()
