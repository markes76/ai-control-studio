---
name: AI Control Studio
description: Pixel Workshop native Mac control panel
colors:
  navy: "rgb(4% 13% 24%)"
  paper: "rgb(98% 97% 93%)"
  muted: "rgb(36% 40% 45%)"
  table-background: "#ffffff"
  teal: "rgb(16% 56% 58%)"
  tint: "rgb(76% 90% 86%)"
  coral: "rgb(96% 39% 31%)"
  switch-off: "rgb(80% 81% 80%)"
typography:
  headline-connections:
    fontFamily: "system-ui"
    fontSize: "30px"
    fontWeight: 600
  headline-catalog:
    fontFamily: "system-ui"
    fontSize: "28px"
    fontWeight: 600
  window-title:
    fontFamily: "system-ui"
    fontSize: "22px"
    fontWeight: 600
  sidebar-title:
    fontFamily: "system-ui"
    fontSize: "20px"
    fontWeight: 600
  routing-title:
    fontFamily: "system-ui"
    fontSize: "18px"
    fontWeight: 600
  inspector-title:
    fontFamily: "system-ui"
    fontSize: "17px"
    fontWeight: 600
  body:
    fontFamily: "system-ui"
    fontSize: "13px"
    fontWeight: 400
  connector-title:
    fontFamily: "system-ui"
    fontSize: "13px"
    fontWeight: 500
  label:
    fontFamily: "system-ui"
    fontSize: "12px"
    fontWeight: 400
  button-primary:
    fontFamily: "system-ui"
    fontSize: "13px"
    fontWeight: 600
  strapline:
    fontFamily: "system-ui"
    fontSize: "10px"
    fontWeight: 500
  source-details:
    fontFamily: "ui-monospace"
    fontSize: "11px"
    fontWeight: 400
rounded:
  ink-button: "6px"
  ink-button-inset: "4px"
  catalog-selection: "6px"
  sidebar-selection: "7px"
  catalog-container: "10px"
components:
  install-button:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.paper}"
    typography: "{typography.button-primary}"
    rounded: "{rounded.ink-button}"
    width: "105px"
    height: "34px"
  apply-button:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.paper}"
    typography: "{typography.button-primary}"
    rounded: "{rounded.ink-button}"
    width: "150px"
    height: "38px"
  sidebar-item:
    backgroundColor: "{colors.tint}"
    textColor: "{colors.navy}"
    rounded: "{rounded.sidebar-selection}"
    width: "204px"
    height: "54px"
  catalog-container:
    backgroundColor: "{colors.table-background}"
    rounded: "{rounded.catalog-container}"
    width: "610px"
    height: "360px"
---

# Design System: AI Control Studio

## Overview

**Creative North Star: "Pixel Workshop"**

A practical and elegant daily Mac control panel expressed as Pixel Workshop: warm cream surfaces, navy ink, teal controls and miniature isometric block artwork. The user approved this direction and its tactile outlined buttons while preserving the native utility layout.

SF system typography and a clear split-view keep the application usable as a daily tool. Generated transparent artwork adds a small workshop identity; live AppKit controls, text and configuration state carry the interaction. Authentic provider artwork remains distinct from the generated identity assets.

**Key Characteristics:**
- Warm cream and navy ink
- Teal selection and routing controls
- Tactile outlined buttons with short offset shadows
- Generated isometric block identity; authentic provider marks
- Native AppKit keyboard and action semantics

This approved refresh extracts `VisualStyle.swift`, `main.swift` and `CatalogView.swift`. The direction reference is `.impeccable/mocks/pixel-workshop/approved.png`; final rendered references are `.impeccable/review/pixel-connections.png` and `.impeccable/review/pixel-catalog.png`. Native geometry uses AppKit points; portable frontmatter uses CSS `px` as a 1:1 logical-unit representation. Font weights map regular/medium/semibold to 400/500/600.

## Colors

Warm cream and navy ink anchor the palette; teal and soft mint communicate interaction.

### Primary
- **Navy Ink** (`navy`): headings, symbols, button faces and outlines.

### Secondary
- **Workshop Teal** (`teal`): enabled routing switches and increased-contrast catalog selection.
- **Mint Tint** (`tint`): selected sidebar items, catalog selection and primary-button inner keyline.

### Tertiary
- **Coral Detail** (`coral`): source-declared accent matching the artwork direction. No current AppKit control consumes this constant; do not infer a status meaning from it.

### Neutral
- **Warm Cream** (`paper`): shell, sidebar, content, secondary button faces, primary button text and switch knobs.
- **Muted Slate** (`muted`): supporting instructions and publisher/status text.
- **Table White** (`table-background`): catalog table.
- **Switch Gray** (`switch-off`): off-state routing track.
- **System semantics**: `NSColor.labelColor`, `systemRed`, field bezels and focus rings remain AppKit-owned. The current window requests `.aqua`; system semantics are not fixed palette swatches. Dividers now use navy at 20% alpha, not system separator color.

**The System Color Rule.** Preserve AppKit semantic text, destructive and focus colors where the source uses them; use the authored palette for custom-drawn controls.

## Typography

Use SF through AppKit system fonts, with system monospaced text in source-detail dialogs. Semibold headings anchor a quiet utility hierarchy; medium connector names and regular small labels keep dense rows readable. The frontmatter records observed roles. Connections supporting copy additionally uses regular 14-point type; InkButton titles use 13-point regular text, or semibold for primary actions; the uppercase window strapline uses 10-point medium text. No custom line-height or tracking is established.

## Layout

The implemented window has fixed content dimensions (1320 × 740 points), with no resizable style mask. The cream sidebar is 240 points wide; the content tab frame begins at x=260. The title is hidden, the titlebar is transparent without a separator, and full-size content extends behind it. Native traffic-light controls remain; background dragging moves the window. There are no web breakpoints or mobile layouts.

Connections uses three open rows on a 100-point vertical pitch, leading 70-point client artwork, aligned titles and trailing 62 × 32-point switch frames. Catalog uses a 610 × 360-point table and an adjacent 335-point inspector, separated by a 1-point navy divider at local x=653. The inspector starts at local x=678 and its heading at x=743. The 1100-point content tab begins at x=260; its surfaces are 1080 points wide. Connector, Connection and Registered columns use widths of 385, 80 and 125 points respectively. Search is 570 × 32 points, filter 220 × 32 points. Catalog rows are 58 points high with 2-point intercell spacing. Provider images fit proportionally inside 34-point row and 50-point inspector frames. Status and explanatory notes occupy the bottom edge of each workspace.

## Elevation & Depth

Depth is tactile but compact. InkButton draws a solid offset rounded silhouette rather than a blurred shadow: navy at 18% alpha, offset 2 points right and 3 points down; disabled shadows fall to 6%. The pressed face shifts 1 point right and 2 points down. Switch knobs use a navy 18% silhouette offset 1 point down. These are AppKit drawn paths, not CSS shadows. Workspace rows remain flat, with navy 20% dividers. No custom easing or animation duration is implemented.

## Shapes

Selection is gently curved: sidebar items use the `sidebar-selection` radius, catalog selection uses `catalog-selection`, and the scroll container uses `catalog-container`. Catalog selection insets the row by 4 points horizontally and 1 point vertically. InkButton faces use the `ink-button` radius and a 1.2-point outline; the primary inner keyline uses the `ink-button-inset` radius and a 0.6-point stroke. WorkshopSwitch uses a capsule track and circular knob. Search, popups and alerts retain native silhouettes. Open connection rows are divided by rules rather than card borders.

## Components

### Buttons

InkButton subclasses `NSButton`, retaining native target/action, keyboard activation and accessibility. Its face is inset 3 points horizontally and 4 vertically. Enabled primary buttons use navy faces, cream text, a navy 75% outer outline and mint 65% inner keyline. Secondary buttons use cream faces and navy text; destructive titles use semantic system red. Disabled faces become cream, outlines fall to navy 18% and text to muted slate 45%. Primary actions include Install and Apply; Apply retains Return as its key equivalent. Focus draws an AppKit focus ring. There is no authored hover treatment or animation. InkButton draws `title` directly; older attributed-title/bezel properties are not its drawing source.

### Inputs / Fields

Search uses `NSSearchField`, filters use `NSPopUpButton`, and model choice uses `NSComboBox` with a 400 × 30-point frame. Configuration alerts use native text fields or secure fields. Keep native keyboard focus and disabled states.

### Navigation

Two icon-leading inline toggle buttons select Connections or MCP Catalog. Selected items use a padded mint-tinted ink bezel, cream inner keyline and subtle offset shadow; unselected items are transparent. Both use 20-point icons and 15-point text within a 204 × 54-point target. Each exposes its selected accessibility value. The sidebar uses the same cream PaperView as the workspace.

### Catalog Container and Selection

A white table sits in a softly curved scroll container without an authored border or shadow. Connector names are one line, tail-truncated, with publisher text below. Mint selection fills use 85% alpha when emphasized and 45% otherwise. Emphasized selection has a 1-point navy outline at 45% alpha. Increased contrast changes fill to teal at 35% and outline to opaque navy at 2 points. Preserve this state distinction.

### Routing Switches

WorkshopSwitch subclasses `NSButton` with switch button type and explicit checkbox accessibility role, preserving native target/action and keyboard semantics. Each has a per-client accessibility label. The on track uses teal with navy 80% outline; off uses switch gray with navy 35% outline. Track stroke is 1.2 points, knob stroke 0.8 points at navy 40%, and the knob face is cream. Keyboard focus uses an AppKit focus ring. State changes are immediate; pictured states in the approved concept do not replace actual routing values. No custom disabled track treatment is implemented.

### Identity and Provider Artwork

`workshop-mark.png`, `workshop-header.png`, `workshop-desktop.png`, `workshop-code.png` and `workshop-codex.png` are generated transparent raster artwork: miniature isometric cream/teal blocks with navy outlines and small coral accents. They are not authored vector geometry. The approved concept is `.impeccable/mocks/pixel-workshop/approved.png`; it establishes direction rather than runtime state. The source displays mark at 86 × 86, header at 280 × 146 and client illustrations at 70 × 70 points. WorkshopArt scans 8-bit alpha values above 24 to find the painted subject, adds approximately 12 pixels of source padding, and proportionally centers that source region in its layout frame. This changes rendering only; it does not crop or modify the asset file. Artwork views are excluded from accessibility because adjacent controls and labels carry meaning. Artwork provenance should accompany each shipping raster. The older `switch-mark.svg` belongs to the previous identity and must not be described as the source of the workshop PNGs.

Provider artwork remains sourced from public Claude directory icon URLs. `assets/logos/sources.json` records origins; `assets/logo-index.json` maps directory IDs to cached images. Missing artwork uses `puzzlepiece.extension`. A service mark is not a publisher claim: Microsoft 365 local explicitly identifies Softeria as independent publisher. The generated workshop assets do not replace provider logos.

## Do's and Don'ts

### Do:
- **Do** use InkButton and WorkshopSwitch for the implemented workshop controls while retaining native actions and keyboard semantics.
- **Do** use mint selection, teal enabled routing and navy hierarchy as implemented.
- **Do** preserve explicit publisher labels alongside service marks.
- **Do** preserve focus rings and increased-contrast catalog selection.

### Don't:
- **Don't** describe generated workshop PNGs as vector artwork.
- **Don't** substitute illustrated switch states for live configuration.
- **Don't** imply a provider logo identifies the implementation publisher.
- **Don't** add broad blurred card shadows to the flat workspace.

### Pixel app identity

The macOS application icon uses `assets/pixel-switch-icon.png`: a chunky pixel-art gateway switch in cream, navy and teal with coral indicators. `PixelSwitch.iconset` and `PixelSwitch.icns` are its size derivatives. Earlier Workshop artwork remains the client illustration family.

Inside the sidebar, use `assets/pixel-switch-sidebar.png`, retaining only the light tile with a transparent exterior.
