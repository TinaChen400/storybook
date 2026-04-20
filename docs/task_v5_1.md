# Task Tracker: V5.1 Interaction Polish

- [x] Fix Race Condition & Re-triggering (`app.js`)
    - [x] Update `stopVoice` to prevent old callbacks from clearing new UI
    - [x] Ensure `playCurrentHotspot` resets all state
- [x] Implement Draggable Interface (`app.js`)
    - [x] Create `makeElementDraggable` helper
    - [x] Initialize dragging for `.caption-bar`
- [x] Add Close Button & Transparency (`index.html`, `style.css`)
    - [x] Add HTML structure for handle/close btn
    - [x] Update CSS for better glass effect
    - [x] Set high Z-index for Spotlight elements
- [x] Improve Word Sync Reliability (`app.js`)
    - [x] Debug `onboundary` charIndex mapping
- [x] Manual Verification
    - [x] Test re-triggering logic
    - [x] Test dragging/closing functionality
- [x] Commit & Push to Git
- [x] Create `walkthrough_v5_1.md`
