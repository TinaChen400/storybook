# Plan: Layout-Aware Auto-OCR & Translation Engine [MIGRATED]

Transform the reading experience by automatically identifying "Image + Text" groups and generating persistent cloud hotspots.

## Implementation Details
- **Trigger**: Automatic 1.5s delay after page load if no hotspots exist.
- **Backend**: Uses `TranslationController.kt` for batch translation via MyMemory API.
- **Logic**: Expand bounding boxes by 5% to group images with text.
- **Persistence**: Save results to MySQL `hotspots` table.
