from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from paddleocr import PaddleOCR
from pydantic import BaseModel
from PIL import Image
import io
import base64
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use stable PaddleOCR 2.7.x
ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)

class OCRRequest(BaseModel):
    image: str

def merge_blocks(raw_results):
    """
    Advanced Column-Aware Merging Algorithm.
    Groups lines into columns first, then merges vertically within columns.
    """
    if not raw_results or not raw_results[0]:
        return [], []

    lines = []
    for line in raw_results[0]:
        points = line[0]
        text, confidence = line[1]
        
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        
        lines.append({
            "text": text,
            "confidence": confidence,
            "x0": x0, "y0": y0, "x1": x1, "y1": y1,
            "cx": (x0 + x1) / 2, # Center X
            "h": y1 - y0
        })

    if not lines:
        return [], []

    # 1. Column Clustering (Group lines that occupy similar horizontal space)
    # We sort by X center first
    lines.sort(key=lambda l: l['x0'])
    
    columns = []
    if lines:
        current_col = [lines[0]]
        for i in range(1, len(lines)):
            prev = current_col[-1]
            curr = lines[i]
            
            # If current line overlaps significantly with the column's horizontal range
            # We use a simple overlap check
            col_x0 = min([l['x0'] for l in current_col])
            col_x1 = max([l['x1'] for l in current_col])
            
            overlap = max(0, min(col_x1, curr['x1']) - max(col_x0, curr['x0']))
            # If overlap is more than 40% of the thinner line, consider it same column region
            # This helps group multi-column layouts correctly
            if overlap > (min(col_x1-col_x0, curr['x1']-curr['x0']) * 0.4):
                current_col.append(curr)
            else:
                columns.append(current_col)
                current_col = [curr]
        columns.append(current_col)

    final_blocks = []

    # 2. Intra-Column Merging (Improved with stricter rules)
    for col in columns:
        # Sort lines within column by Y
        col.sort(key=lambda l: l['y0'])
        
        merged_groups = []
        if not col: continue
        
        current_group = [col[0]]
        for i in range(1, len(col)):
            prev = current_group[-1]
            curr = col[i]
            
            dy = curr['y0'] - prev['y1']
            
            # V7 Optimization: Stricter Alignment and Proximity
            # Only merge if:
            # 1. Vertical gap is small (1.2x line height)
            # 2. Left edges are roughly aligned (within 15px) - suggests same paragraph
            # 3. Or center points are very close horizontally
            
            dx_left = abs(curr['x0'] - prev['x0'])
            is_aligned = dx_left < 15
            
            if dy < (prev['h'] * 1.2) and is_aligned:
                current_group.append(curr)
            else:
                merged_groups.append(current_group)
                current_group = [curr]
        merged_groups.append(current_group)

        # 3. Form final blocks for this column
        for group in merged_groups:
            merged_text = " ".join([l['text'] for l in group])
            avg_conf = sum([l['confidence'] for l in group]) / len(group)
            
            gx0 = min([l['x0'] for l in group])
            gy0 = min([l['y0'] for l in group])
            gx1 = max([l['x1'] for l in group])
            gy1 = max([l['y1'] for l in group])

            final_blocks.append({
                "text": merged_text,
                "confidence": round(float(avg_conf), 3),
                "bbox": {
                    "x0": int(gx0),
                    "y0": int(gy0),
                    "x1": int(gx1),
                    "y1": int(gy1)
                }
            })

    return final_blocks, lines  # Return both blocks and raw lines for paragraph processing

def filter_and_merge_paragraphs(blocks, raw_lines, img_w, img_h):
    """
    1. Filter out blocks covering >90% of page area (noise blocks)
    2. Apply 2% padding (narrower than previous 5%)
    Note: Removed Header-Body merging - it was too aggressive and merged everything
    """
    if not blocks:
        return []
    
    paragraphs = []
    page_area = img_w * img_h
    
    for block in blocks:
        bbox = block.get("bbox", {})
        x0, y0, x1, y1 = bbox.get("x0", 0), bbox.get("y0", 0), bbox.get("x1", 0), bbox.get("y1", 0)
        
        # 1. Filter: Discard blocks covering >90% of page (likely false positives/noise)
        block_area = (x1 - x0) * (y1 - y0)
        if block_area > page_area * 0.9:
            continue
        
        paragraphs.append(block)
    
    # 2. Apply 2% padding (narrower than previous 5%)
    padding = 0.02
    for p in paragraphs:
        bbox = p.get("bbox", {})
        w = bbox.get("x1", 0) - bbox.get("x0", 0)
        h = bbox.get("y1", 0) - bbox.get("y0", 0)
        pad_x = w * padding
        pad_y = h * padding
        
        p["bbox"] = {
            "x0": max(0, int(bbox.get("x0", 0) - pad_x)),
            "y0": max(0, int(bbox.get("y0", 0) - pad_y)),
            "x1": min(img_w, int(bbox.get("x1", 0) + pad_x)),
            "y1": min(img_h, int(bbox.get("y1", 0) + pad_y))
        }
    
    return paragraphs

@app.get("/health")
def health_check():
    return {"status": "ok", "engine": "PaddleOCR + Column-Aware Merger"}

@app.post("/ocr")
async def ocr_endpoint(request: OCRRequest):
    try:
        image_data = base64.b64decode(request.image)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        img_w, img_h = image.size
        img_array = np.array(image)
        
        raw_result = ocr.ocr(img_array, cls=True)
        blocks, raw_lines = merge_blocks(raw_result)
        
        # Process paragraphs with filtering and merging
        paragraphs = filter_and_merge_paragraphs(blocks, raw_lines, img_w, img_h)
        
        for b in blocks:
            b["image_width"] = img_w
            b["image_height"] = img_h
        
        for p in paragraphs:
            p["image_width"] = img_w
            p["image_height"] = img_h
                    
        return {
            "blocks": blocks, 
            "paragraphs": paragraphs,
            "count": len(blocks),
            "paragraphCount": len(paragraphs)
        }
    except Exception as e:
        print(f"Server Error: {str(e)}")
        return {"error": str(e), "blocks": [], "paragraphs": [], "count": 0, "paragraphCount": 0}
