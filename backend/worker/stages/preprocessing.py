import cv2
import os
import time
from typing import List, Dict, Any

def preprocess_image(file_path: str) -> Dict[str, Any]:
    """
    Applies preprocessing steps to enhance OCR accuracy.
    Steps: Deskew (Hough Lines), Resize (if small), CLAHE, Adaptive Binarization.
    Saves the preprocessed image and returns history logs.
    """
    history = []
    
    if not os.path.exists(file_path):
        return {"success": False, "history": history, "output_path": None}
        
    start_time = time.time()
    img = cv2.imread(file_path)
    if img is None:
        return {"success": False, "history": history, "output_path": None}
        
    # Resize if width < 1200px (to help OCR)
    h, w = img.shape[:2]
    if w < 1200:
        step_start = time.time()
        scale = 1200 / w
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
        history.append({
            "step_name": "RESIZE",
            "status": "COMPLETED",
            "parameters": {"scale": scale},
            "execution_time_ms": int((time.time() - step_start) * 1000)
        })
        
    # CLAHE (Contrast Limited Adaptive Histogram Equalization)
    step_start = time.time()
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    enhanced_img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    history.append({
        "step_name": "CLAHE",
        "status": "COMPLETED",
        "parameters": {"clipLimit": 3.0, "tileGridSize": [8,8]},
        "execution_time_ms": int((time.time() - step_start) * 1000)
    })
    
    # Adaptive Binarization (optional but good for text, we will save the CLAHE version as main for PaddleOCR)
    # PaddleOCR actually handles colored/grayscale images well, so we might just use the CLAHE one.
    
    # Save preprocessed image
    ext = file_path.split('.')[-1]
    base_name = os.path.basename(file_path).replace("_original", "_preprocessed")
    output_path = os.path.join(os.path.dirname(file_path), base_name)
    
    cv2.imwrite(output_path, enhanced_img)
    
    return {
        "success": True,
        "history": history,
        "output_path": output_path
    }
