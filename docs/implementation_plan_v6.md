# Implementation Plan V6: Invisible Interactive UI

Transform the reader into a clean, minimalist experience where hotspots are invisible by default and do not obscure the original artwork or text.

## User Review Required

> [!IMPORTANT]
> **Visibility Logic**: Hotspots will be **100% invisible** until clicked. This means you will see the pure book page. When you click an area, the spotlight effect and caption bar will appear as usual.
> **Removal of Labels**: The white text boxes in the middle of the page will be removed entirely, as the text is now elegantly displayed in the bottom caption bar.

## Proposed Changes

### [Component] Interface Logic (JavaScript)

#### [MODIFY] [app.js](file:///d:/Dev/stroybook/interactive_reader/app.js)
- **Simplify `renderHotspots`**: Remove the line that injects `hotspot-text` into the box.
- This ensures no floating labels block the view.

### [Component] Styling (CSS)

#### [MODIFY] [style.css](file:///d:/Dev/stroybook/interactive_reader/style.css)
- **Base State (`.hotspot-box`)**: Set `border: none` and `background: transparent`.
- **Hover State (`.hotspot-box:hover`)**: (Optional) Add an extremely subtle 1px dashed white border to give a tiny hint of interactivity.
- **Active State (`.hotspot-box.reading`)**: Retain the high-contrast spotlight effect and gold border so users know exactly what is being read.

## Verification Plan

### Manual Verification
1.  **Open a book**: The page should look clean, with no boxes or red borders.
2.  **Click a text area**: The spotlight should appear, and reading should start with the caption bar.
3.  **Visual Clarity**: Verify that the artwork is no longer obscured by white text boxes.
