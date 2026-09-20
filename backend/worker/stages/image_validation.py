import os
from PIL import Image
import cv2
import numpy as np
from typing import Dict, Any

def validate_image(file_path: str) -> Dict[str, Any]:
    """
    Validates the image file and computes quality scores.
    Returns a dictionary of updates for the images table.
    """
    result = {
        "is_valid_file": False,
        "resolution_width": None,
        "resolution_height": None,
        "blur_score": None,
        "glare_score": None,
        "preprocessing_status": "FAILED"
    }
    
    if not os.path.exists(file_path):
        return result
        
    try:
        # Verify with PIL
        with Image.open(file_path) as img:
            img.verify()
            
        # Re-open to get properties since verify() closes it
        with Image.open(file_path) as img:
            result["resolution_width"] = img.width
            result["resolution_height"] = img.height
            
        # Read with OpenCV for quality scores
        cv_img = cv2.imread(file_path)
        if cv_img is None:
            return result
            
        # Blur score (Laplacian variance)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        # Normalize blur score (higher is sharper, limit to 1.0 for our schema)
        normalized_blur = min(blur_score / 1000.0, 1.0)
        result["blur_score"] = normalized_blur
        
        # Glare score (ratio of very bright pixels)
        bright_pixels = np.sum(gray > 240)
        total_pixels = gray.shape[0] * gray.shape[1]
        glare_score = bright_pixels / total_pixels
        result["glare_score"] = min(glare_score, 1.0)
        
        result["is_valid_file"] = True
        result["preprocessing_status"] = "UNPROCESSED" # Ready for next step
        
    except Exception as e:
        print(f"Validation failed for {file_path}: {e}")
        
    return result
