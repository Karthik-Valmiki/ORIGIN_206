"""
CV Processor — OpenCV-based image quality assessment and preprocessing.
All functions are SYNCHRONOUS (run via asyncio.run_in_executor in pipeline_svc).
"""

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np


@dataclass
class CVResult:
    is_usable: bool
    processed_path: str        # path to the preprocessed image
    resolution_width: int
    resolution_height: int
    blur_score: float          # 0=sharp .. 1=blurry (inverted Laplacian variance)
    glare_score: float         # 0=no glare .. 1=severe glare
    reflection_score: float
    orientation_angle: int     # 0 | 90 | 180 | 270
    rejection_reason: str | None = None


def _blur_score(gray: np.ndarray) -> float:
    """Laplacian variance: low = blurry. Inverted & normalised to 0-1."""
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    # Empirically, < 100 = blurry for product label images
    score = max(0.0, 1.0 - min(lap_var / 500.0, 1.0))
    return round(score, 4)


def _glare_score(gray: np.ndarray) -> float:
    """Fraction of pixels that are over-exposed (>240)."""
    total = gray.size
    overexposed = np.sum(gray > 240)
    return round(float(overexposed / total), 4)


def _reflection_score(gray: np.ndarray) -> float:
    """High local standard-deviation spots = reflections."""
    blur = cv2.GaussianBlur(gray, (21, 21), 0)
    diff = cv2.absdiff(gray, blur)
    score = float(diff.mean()) / 255.0
    return round(min(score * 3, 1.0), 4)


def _orientation_angle(img: np.ndarray) -> int:
    """Heuristic: landscape = 0, portrait = 90. Extend with EXIF if needed."""
    h, w = img.shape[:2]
    return 0 if w >= h else 90


def _preprocess(img: np.ndarray) -> np.ndarray:
    """
    Standard preprocessing pipeline for OCR readiness:
    1. Resize to 300-DPI equivalent width (1800px)
    2. Denoise
    3. CLAHE contrast enhancement
    4. Unsharp mask sharpen
    """
    h, w = img.shape[:2]
    target_w = 1800
    if w < target_w:
        scale = target_w / w
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Denoise
    img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

    # CLAHE on L channel
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    img = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    # Unsharp mask
    gaussian = cv2.GaussianBlur(img, (0, 0), 3)
    img = cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)

    return img


def process(file_path: str) -> CVResult:
    """
    Full CV pipeline for one image.
    Returns CVResult with is_usable=False if image is too degraded.
    """
    img = cv2.imread(file_path)
    if img is None:
        return CVResult(
            is_usable=False, processed_path=file_path,
            resolution_width=0, resolution_height=0,
            blur_score=1.0, glare_score=0.0, reflection_score=0.0,
            orientation_angle=0, rejection_reason="Cannot read image file",
        )

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    blur = _blur_score(gray)
    glare = _glare_score(gray)
    reflection = _reflection_score(gray)
    angle = _orientation_angle(img)

    # Quality gate
    if blur > 0.85:
        return CVResult(
            is_usable=False, processed_path=file_path,
            resolution_width=w, resolution_height=h,
            blur_score=blur, glare_score=glare, reflection_score=reflection,
            orientation_angle=angle, rejection_reason="Image too blurry",
        )

    if w < 200 or h < 200:
        return CVResult(
            is_usable=False, processed_path=file_path,
            resolution_width=w, resolution_height=h,
            blur_score=blur, glare_score=glare, reflection_score=reflection,
            orientation_angle=angle, rejection_reason="Resolution too low",
        )

    # Rotate if portrait
    if angle == 90:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

    processed = _preprocess(img)

    # Save to <original_stem>_processed.<ext>
    p = Path(file_path)
    processed_path = str(p.parent / f"{p.stem}_processed{p.suffix}")
    cv2.imwrite(processed_path, processed)

    ph, pw = processed.shape[:2]
    return CVResult(
        is_usable=True, processed_path=processed_path,
        resolution_width=pw, resolution_height=ph,
        blur_score=blur, glare_score=glare, reflection_score=reflection,
        orientation_angle=angle,
    )
