# Implementation Plan V5.2: Multi-Language Word Sync Fix

Resolve the issue where word-level highlighting fails, especially for Chinese text, by implementing locale-aware text segmentation.

## User Review Required

> [!IMPORTANT]
> **Chinese Text Segmentation**: Since Chinese doesn't use spaces, the previous logic treated entire paragraphs as a single "word". I will now split Chinese text by character or word-segments to ensure the highlight moves smoothly.
> **Voice Compatibility**: I will add console logging so we can verify if your specific browser voice is sending the "boundary" events required for this feature.

## Proposed Changes

### [Component] Logic (JavaScript)

#### [MODIFY] [app.js](file:///d:/Dev/stroybook/interactive_reader/app.js)
- **Locale-Aware Splitting**: Implement a new `renderTextWithIndices(text, lang)` function.
    - Uses `Intl.Segmenter` (if available) to correctly identify word boundaries for both English and Chinese.
    - Fallback logic: Splits by whitespace/punctuation for English, and by character for Chinese.
- **Improved Boundary Logic**: 
    - Ensure `charIndex` correctly maps to the segmented spans.
    - Add a "Spotlight fallback": if word-level data is missing from the voice, keep the paragraph highlight as a second-best indicator.

### [Component] Styling (CSS)

#### [MODIFY] [style.css](file:///d:/Dev/stroybook/interactive_reader/style.css)
- **Active Word Visibility**: Enhance the `.reading-word.active` style with a stronger background glow or underline to make it more obvious.

## Verification Plan

### Manual Verification
1.  **English Test**: Click an English paragraph. Words should highlight one by one.
2.  **Chinese Test**: Click a Chinese paragraph. Words (or characters) should highlight one by one.
3.  **Console Check**: Open F12 console and look for "Boundary Event" logs to confirm system triggers.
