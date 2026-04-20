# Plan: Refined Spatial Grouping for Auto-OCR

Fix the "Single Large Block" issue by implementing fine-grained layout analysis and proximity-based clustering.

## User Review Required

> [!IMPORTANT]
> **Switch to Line-Level Analysis**: We will move away from Tesseract's automatic block detection, which is failing on this layout, and instead group individual lines based on their physical distance. This will ensure that side-by-side sections or independent image/text pairs are correctly separated.

## Proposed Changes

### 1. Frontend Logic (app.js)

#### [MODIFY] [app.js](d:\Dev\stroybook\interactive_reader\app.js)
- **`autoAnalyzePage()`**:
    - Change `result.data.blocks` to `result.data.paragraphs`.
    - Implement a **Filter**: Discard any paragraph that covers more than 90% of the page area.
    - Implement **Header-Body Merging**: If a very short line (likely a title) is immediately above a paragraph, merge them into one hotspot.
    - **Bounding Box Padding**: Narrow the padding from 5% to 2% to prevent overlapping with nearby groups.

## Verification Plan
1. **Multi-Section Test**: Open the "Army Life" page. Verify that instead of one giant box, multiple boxes appear around each coin/soldier/fort section.
2. **Column Test**: Verify that text in the left column does not get merged with text in the right column.
