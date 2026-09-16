from typing import List, Dict, Any
from rapidfuzz import fuzz
from ..anchors import ANCHORS

def _get_center(bbox):
    # bbox is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    return (sum(xs)/4, sum(ys)/4)

def _is_to_right(anchor_center, target_center, y_threshold=20):
    # Target is to the right if target x > anchor x and y diff is small
    return target_center[0] > anchor_center[0] and abs(target_center[1] - anchor_center[1]) < y_threshold

def _is_below(anchor_center, target_center, x_threshold=50):
    # Target is below if target y > anchor y and x diff is small
    return target_center[1] > anchor_center[1] and abs(target_center[0] - anchor_center[0]) < x_threshold

def extract_fields(ocr_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Matches OCR text against anchors using fuzzy matching.
    Then finds nearby text (right or below) as the value.
    """
    extracted = []
    
    # Simple algorithm for the prototype:
    # 1. For each field type and anchor, find the best matching OCR token (fuzz.ratio >= 80)
    # 2. If found, find the closest token to its right or directly below
    
    for field_type, anchors in ANCHORS.items():
        best_anchor_match = None
        best_score = 0
        anchor_token = None
        
        for token in ocr_results:
            text = token["detected_text"]
            for anchor in anchors:
                score = fuzz.ratio(text.lower(), anchor.lower())
                if score > best_score and score >= 80:
                    best_score = score
                    anchor_token = token
                    best_anchor_match = anchor
                    
        if anchor_token:
            anchor_center = _get_center(anchor_token["bounding_box"])
            
            # Find closest candidate value
            best_candidate = None
            min_dist = float('inf')
            
            for token in ocr_results:
                if token == anchor_token:
                    continue
                    
                target_center = _get_center(token["bounding_box"])
                
                # Check if it's spatially related (right or below)
                if _is_to_right(anchor_center, target_center) or _is_below(anchor_center, target_center):
                    # distance = Euclidean distance between centers
                    dist = ((target_center[0] - anchor_center[0])**2 + (target_center[1] - anchor_center[1])**2)**0.5
                    if dist < min_dist:
                        min_dist = dist
                        best_candidate = token
                        
            if best_candidate:
                extracted.append({
                    "field_type": field_type,
                    "raw_value": best_candidate["detected_text"],
                    "confidence": float(best_candidate["confidence_score"]),
                    "ocr_result": best_candidate # to keep the ID later
                })
                
    return extracted
