# Implementation Plan V5: Read-Along Synchronization Upgrade

Improve the user's reading experience by adding visual feedback for the current reading position, including a spotlight effect on the page and a large-text caption bar at the bottom.

## User Review Required

> [!IMPORTANT]
> **Subtitle Bar Placement**: The caption bar will be fixed at the bottom of the screen. We will ensure it doesn't overlap with the page navigation buttons.
> **Highlighting Precision**: Word-level highlighting relies on individual system voices. Some older voices might not trigger `onboundary` events reliably; we will provide a fallback that highlights the entire paragraph if word events fail.

## Proposed Changes

### [Component] Styling (CSS)

#### [MODIFY] [style.css](file:///d:/Dev/stroybook/interactive_reader/style.css)
- Add `.caption-bar`: A fixed-bottom container with glassmorphism style.
- Add `.reading-word`: High-contrast style for keywords in the caption bar.
- Add `.hotspot-box.reading`: A "spotlight" style (thicker border, soft glow) for the active paragraph.
- Add `.reading-overlay`: A global dimming effect when reading starts (optional, for focus).

### [Component] Interface (HTML)

#### [MODIFY] [index.html](file:///d:/Dev/stroybook/interactive_reader/index.html)
- Add `<div id="caption-bar" class="hidden"></div>` to the `reader-view`.

### [Component] Logic (JavaScript)

#### [MODIFY] [app.js](file:///d:/Dev/stroybook/interactive_reader/app.js)
- Update `playCurrentHotspot()`:
    - Clear existing reading highlights.
    - Identify current box and apply `.reading` class.
    - Show and populate `caption-bar` with the paragraph text.
    - Attach `onboundary` event to `SpeechSynthesisUtterance`.
    - Implement `highlightWord(charIndex)` to update the caption bar in real-time.
    - Implement cleanup logic in `onend`.

## Verification Plan

### Automated/Interactive Verification
- Use the browser tool to trigger a hotspot click.
- Verify that `caption-bar` appears and updates its content.
- Verify that the active hotspot box changes color.

### Manual Verification
- Confirm that reading a long paragraph of text remains easy to follow visually.
