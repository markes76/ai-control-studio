import AppKit

struct Studio {
    static let navy = NSColor(srgbRed:0.04,green:0.13,blue:0.24,alpha:1)
    static let paper = NSColor(srgbRed:0.98,green:0.97,blue:0.93,alpha:1)
    static let teal = NSColor(srgbRed:0.16,green:0.56,blue:0.58,alpha:1)
    static let tint = NSColor(srgbRed:0.76,green:0.90,blue:0.86,alpha:1)
    static let coral = NSColor(srgbRed:0.96,green:0.39,blue:0.31,alpha:1)
    static let muted = NSColor(srgbRed:0.36,green:0.40,blue:0.45,alpha:1)
    static func text(_ value:String,_ rect:NSRect,_ size:CGFloat,_ weight:NSFont.Weight = .regular,_ color:NSColor = .labelColor)->NSTextField {
        let f=NSTextField(wrappingLabelWithString:value);f.frame=rect;f.font = .systemFont(ofSize:size,weight:weight);f.textColor=color;return f
    }
    static func line(_ rect:NSRect)->NSView {let v=NSView(frame:rect);v.wantsLayer=true;v.layer?.backgroundColor=Studio.navy.withAlphaComponent(0.20).cgColor;return v}
    static func artwork(_ name:String,_ rect:NSRect)->NSView {WorkshopArt(name:name,frame:rect)}
    static func symbol(_ name:String,_ rect:NSRect)->NSImageView {let v=NSImageView(frame:rect);v.image=NSImage(systemSymbolName:name,accessibilityDescription:nil);v.contentTintColor=navy;v.imageScaling = .scaleProportionallyUpOrDown;return v}
}
final class PaperView:NSView {
    override init(frame:NSRect){super.init(frame:frame);wantsLayer=true;layer?.backgroundColor=Studio.paper.cgColor}
    required init?(coder:NSCoder){fatalError()}
}
final class LogoStore {
    static let shared=LogoStore()
    private var mapping:[String:String]=[:]
    private var images:[String:NSImage]=[:]
    init(){if let url=Bundle.main.url(forResource:"logo-index",withExtension:"json"),let data=try? Data(contentsOf:url),let v=try? JSONSerialization.jsonObject(with:data) as? [String:String]{mapping=v}}
    func image(_ entry:[String:Any])->NSImage? {
        guard let id=entry["_id"] as? String,let file=mapping[id] else{return nil}
        if let image=images[file]{return image}
        guard let url=Bundle.main.resourceURL?.appendingPathComponent("logos/"+file),let image=NSImage(contentsOf:url) else{return nil}
        images[file]=image;return image
    }
}
final class CatalogRow:NSTableRowView {
    override var interiorBackgroundStyle:NSView.BackgroundStyle { .normal }
    override func drawSelection(in dirtyRect:NSRect) {
        let contrast=NSWorkspace.shared.accessibilityDisplayShouldIncreaseContrast
        (contrast ? Studio.teal.withAlphaComponent(0.35) : Studio.tint.withAlphaComponent(isEmphasized ? 0.85:0.45)).setFill()
        let path=NSBezierPath(roundedRect:bounds.insetBy(dx:4,dy:1),xRadius:6,yRadius:6);path.fill()
        if contrast || isEmphasized {Studio.navy.withAlphaComponent(contrast ? 1:0.45).setStroke();path.lineWidth=contrast ? 2:1;path.stroke()}
    }
}

// NSButton retains native keyboard activation and accessibility while its ink bezel is drawn here.
final class InkButton:NSButton {
    var primary=false
    var destructive=false
    override func draw(_ dirtyRect:NSRect) {
        let pressed=isHighlighted
        let face=bounds.insetBy(dx:3,dy:4).offsetBy(dx:pressed ? 1:0,dy:pressed ? -2:0)
        Studio.navy.withAlphaComponent(isEnabled ? 0.18:0.06).setFill()
        NSBezierPath(roundedRect:face.offsetBy(dx:2,dy:-3),xRadius:6,yRadius:6).fill()
        (primary && isEnabled ? Studio.navy : Studio.paper).setFill()
        let path=NSBezierPath(roundedRect:face,xRadius:6,yRadius:6);path.fill()
        Studio.navy.withAlphaComponent(isEnabled ? 0.75:0.18).setStroke();path.lineWidth=1.2;path.stroke()
        if primary && isEnabled {let inset=NSBezierPath(roundedRect:face.insetBy(dx:2,dy:2),xRadius:4,yRadius:4);Studio.tint.withAlphaComponent(0.65).setStroke();inset.lineWidth=0.6;inset.stroke()}
        let color = !isEnabled ? Studio.muted.withAlphaComponent(0.45) : (primary ? Studio.paper : (destructive ? NSColor.systemRed:Studio.navy))
        let attrs:[NSAttributedString.Key:Any]=[.font:NSFont.systemFont(ofSize:13,weight:primary ? .semibold:.regular),.foregroundColor:color]
        let size=title.size(withAttributes:attrs)
        title.draw(at:NSPoint(x:face.midX-size.width/2,y:face.midY-size.height/2),withAttributes:attrs)
        if window?.firstResponder === self {NSGraphicsContext.saveGraphicsState();NSFocusRingPlacement.only.set();path.fill();NSGraphicsContext.restoreGraphicsState()}
    }
}
final class WorkshopSwitch:NSButton {
    override init(frame:NSRect){super.init(frame:frame);setButtonType(.switch);title="";isBordered=false;setAccessibilityRole(.checkBox)}
    required init?(coder:NSCoder){fatalError()}
    override func draw(_ dirtyRect:NSRect){
        let rect=bounds.insetBy(dx:3,dy:4)
        let path=NSBezierPath(roundedRect:rect,xRadius:rect.height/2,yRadius:rect.height/2)
        (state == .on ? Studio.teal:NSColor(srgbRed:0.80,green:0.81,blue:0.80,alpha:1)).setFill();path.fill()
        Studio.navy.withAlphaComponent(state == .on ? 0.8:0.35).setStroke();path.lineWidth=1.2;path.stroke()
        let diameter=rect.height-2
        let knob=NSRect(x:state == .on ? rect.maxX-diameter-1:rect.minX+1,y:rect.minY+1,width:diameter,height:diameter)
        let shadow=NSBezierPath(ovalIn:knob.offsetBy(dx:0,dy:-1));Studio.navy.withAlphaComponent(0.18).setFill();shadow.fill()
        let circle=NSBezierPath(ovalIn:knob);Studio.paper.setFill();circle.fill();Studio.navy.withAlphaComponent(0.40).setStroke();circle.lineWidth=0.8;circle.stroke()
        if window?.firstResponder === self {NSGraphicsContext.saveGraphicsState();NSFocusRingPlacement.only.set();path.fill();NSGraphicsContext.restoreGraphicsState()}
    }
}

// Fit the painted subject, rather than the generator's transparent canvas, into its layout slot.
final class WorkshopArt:NSView {
    private var image:NSImage?
    private var source=NSRect.zero
    init(name:String,frame:NSRect){
        super.init(frame:frame)
        guard let url=Bundle.main.url(forResource:name,withExtension:"png"),let img=NSImage(contentsOf:url),let bytes=try? Data(contentsOf:url),let rep=NSBitmapImageRep(data:bytes) else{return}
        image=img;source=NSRect(origin:.zero,size:img.size)
        if rep.hasAlpha,let data=rep.bitmapData,rep.bitsPerSample==8,rep.samplesPerPixel>=4 {
            var minX=rep.pixelsWide,minY=rep.pixelsHigh,maxX=0,maxY=0
            for y in 0..<rep.pixelsHigh {for x in 0..<rep.pixelsWide {if data[y*rep.bytesPerRow+x*rep.samplesPerPixel+rep.samplesPerPixel-1]>24 {minX=min(minX,x);minY=min(minY,y);maxX=max(maxX,x);maxY=max(maxY,y)}}}
            if maxX>minX,maxY>minY {let sx=img.size.width/CGFloat(rep.pixelsWide),sy=img.size.height/CGFloat(rep.pixelsHigh);source=NSRect(x:CGFloat(max(0,minX-12))*sx,y:CGFloat(max(0,rep.pixelsHigh-maxY-13))*sy,width:CGFloat(min(rep.pixelsWide,maxX-minX+25))*sx,height:CGFloat(min(rep.pixelsHigh,maxY-minY+25))*sy)}
        }
        setAccessibilityElement(false)
    }
    required init?(coder:NSCoder){fatalError()}
    override func draw(_ dirtyRect:NSRect){guard let image=image,source.width>0 else{return};let scale=min(bounds.width/source.width,bounds.height/source.height);let size=NSSize(width:source.width*scale,height:source.height*scale);let dest=NSRect(x:bounds.midX-size.width/2,y:bounds.midY-size.height/2,width:size.width,height:size.height);image.draw(in:dest,from:source,operation:.sourceOver,fraction:1)}
}

final class SidebarButton:NSButton {
    override func draw(_ dirtyRect:NSRect){
        let selected=state == .on
        let rect=bounds.insetBy(dx:3,dy:3)
        if selected {
            Studio.navy.withAlphaComponent(0.20).setFill()
            NSBezierPath(roundedRect:rect.offsetBy(dx:2,dy:2),xRadius:9,yRadius:9).fill()
            Studio.tint.setFill()
            let face=NSBezierPath(roundedRect:rect,xRadius:9,yRadius:9);face.fill()
            Studio.navy.setStroke();face.lineWidth=1.3;face.stroke()
            Studio.paper.withAlphaComponent(0.9).setStroke()
            let inset=NSBezierPath(roundedRect:rect.insetBy(dx:3,dy:3),xRadius:6,yRadius:6);inset.lineWidth=1.2;inset.stroke()
        }
        let color=selected ? Studio.navy:Studio.muted
        let attrs:[NSAttributedString.Key:Any]=[.font:NSFont.systemFont(ofSize:15,weight:selected ? .semibold:.medium),.foregroundColor:color]
        let size=title.size(withAttributes:attrs)
        title.draw(at:NSPoint(x:47,y:bounds.midY-size.height/2),withAttributes:attrs)
        if let source=image,let icon=source.copy() as? NSImage {
            icon.lockFocus();color.set();NSRect(origin:.zero,size:icon.size).fill(using:.sourceAtop);icon.unlockFocus()
            icon.draw(in:NSRect(x:18,y:bounds.midY-10,width:20,height:20),from:.zero,operation:.sourceOver,fraction:1)
        }
        if window?.firstResponder === self {let ring=NSBezierPath(roundedRect:bounds.insetBy(dx:1,dy:3),xRadius:10,yRadius:10);NSGraphicsContext.saveGraphicsState();NSFocusRingPlacement.only.set();ring.fill();NSGraphicsContext.restoreGraphicsState()}
    }
}
