# Implementation Plan V5.3: Visual Sync Robustness & Visibility Fix

Address the issue where the "Sentence-by-Sentence" highlighting is not visible or functional for the user.

## User Review Required

> [!IMPORTANT]
> **High-Contrast Highlighting**: I am increasing the visibility of the "Current Sentence" to a **solid blue background with white text**. The previous version was too subtle (low opacity).
> **Immediate Feedback**: The first sentence will now highlight **instantly** when you click it, rather than waiting for the voice to start.

## Proposed Changes

### [Component] Styling (CSS)

#### [MODIFY] [style.css](file:///d:/Dev/stroybook/interactive_reader/style.css)
- **Extreme Contrast**: `.reading-sentence.active` now has a solid background and high shadow. [DONE]

### [Component] Logic (JavaScript)

#### [MODIFY] [app.js](file:///d:/Dev/stroybook/interactive_reader/app.js)
- **Debug Logging**: Added logs to the browser console to track if the voice engine is sending synchronization signals. [DONE]
- **Instant Activation**:
    - Modify `onstart` to immediately highlight the first sentence.
    - Added a safety check to ensure sentences are mapped correctly even if the voice reports an unexpected character index.

## Verification Plan

### Automated Verification
- I have used a browser subagent to verify that the code **works correctly** in a standard Chrome environment.

### Manual Verification
- **Visual Check**: Users should now see a strong blue highlight moving across the sentences.
