"""
OCR Processor — Tesseract-based OCR.
All functions are SYNCHRONOUS (run via asyncio.run_in_executor in pipeline_svc).
"""

from dataclasses import dataclass
from typing import Any

import cv2
import pytesseract


@dataclass
class OCRResultData:
    detected_text: str
    bounding_box: dict[str, int]
    confidence_score: float
    language: str


def process(file_path: str) -> list[OCRResultData]:
    """
    Run Tesseract OCR on the image.
    Returns a list of detected text blocks with bounding boxes and confidences.
    """
    img = cv2.imread(file_path)
    if img is None:
        return []

    # Use pytesseract to get detailed data including bounding boxes and confidence
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    
    results = []
    n_boxes = len(data['text'])
    for i in range(n_boxes):
        if int(data['conf'][i]) > -1:  # Filter out empty results
            text = data['text'][i].strip()
            if text:
                (x, y, w, h) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                results.append(
                    OCRResultData(
                        detected_text=text,
                        bounding_box={"x1": x, "y1": y, "x2": x + w, "y2": y + h},
                        confidence_score=float(data['conf'][i]) / 100.0,
                        language="en"
                    )
                )

    return results
