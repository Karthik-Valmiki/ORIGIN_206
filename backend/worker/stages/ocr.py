from typing import List, Dict, Any

def run_ocr(ocr_engine, file_path: str) -> List[Dict[str, Any]]:
    """
    Runs PaddleOCR on the image and returns a list of results.
    Each result contains text, bbox (as list of points), and confidence.
    """
    results = []
    try:
        # result is a list of lists. For one image it's result[0]
        # format: [[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ('text', confidence)]
        ocr_output = ocr_engine.ocr(file_path, cls=True)
        if not ocr_output or not ocr_output[0]:
            return results
            
        for line in ocr_output[0]:
            bbox, (text, confidence) = line
            results.append({
                "detected_text": text,
                "bounding_box": bbox,
                "confidence_score": float(confidence),
                "language": "en"
            })
    except Exception as e:
        print(f"OCR failed for {file_path}: {e}")
        
    return results
