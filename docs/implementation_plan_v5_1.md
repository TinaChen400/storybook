# Implementation Plan V5.1: Interaction Polish & Robust Synchronization

Resolve functional issues with the "Read-Along Mode" and add requested UI features (movable, closeable, more transparent).

## User Review Required

> [!IMPORTANT]
> **Draggable Interface**: The caption bar will now have a "drag handle" area. Users can move it anywhere on the screen, and it will remember its position until the page is refreshed.
> **Manual Stop Logic**: We will fix the race condition that prevents the UI from reappearing after a manual stop.
> **Word Sync Fallback**: Since some browsers/voices don't support `onboundary`, we will add a fallback that highlights the entire text block if word-level data is missing.

## Proposed Changes

### [Component] Styling (CSS)

#### [MODIFY] [style.css](file:///d:/Dev/stroybook/interactive_reader/style.css)
- **Glassmorphism**: Reduce `rgba(255, 255, 255, 0.85)` to `rgba(255, 255, 255, 0.4)` for better transparency.
- **Drag Handle**: Add style for `.caption-drag-handle`.
- **Close Button**: Add style for `.caption-close-btn`.
- **Spotlight Fix**: Ensure `.active-reading` and `.reading` have high Z-index.

### [Component] Interface (HTML)

#### [MODIFY] [index.html](file:///d:/Dev/stroybook/interactive_reader/index.html)
- Add a drag handle `div` at the top of the `#caption-bar`.
- Add a close button `×` to the `#caption-bar`.

### [Component] Logic (JavaScript)

#### [MODIFY] [app.js](file:///d:/Dev/stroybook/interactive_reader/app.js)
- **Race Condition Fix**: Update `stopVoice()` to set `utterance.onend = null` before calling `speechSynthesis.cancel()`.
- **Draggable Logic**: Add `makeDraggable(element)` utility.
- **Word Sync Improvement**: Add logging to debug `onboundary` and ensure it targets the correct words.
- **Re-trigger Logic**: Ensure `el.captionBar.classList.remove('hidden')` is always called on fresh clicks.

## Verification Plan

### Manual Verification
1.  **Click & Re-click**: Verify that clicking the same or different hotspots multiple times consistently shows the bar.
2.  **Drag & Close**: Verify the bar can be moved and dismissed via the '×' button.
3.  **Spotlight Check**: Confirm other hotspots dim when one is active.
4.  **Word Tracking**: Observe if word highlighting occurs during playback.
