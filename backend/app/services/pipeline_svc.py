import asyncio
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.inspection import Image, OcrResult, ExtractedField, Finding
from app.pipeline import cv_processor, ocr_processor
from app.database import AsyncSessionLocal


async def run_pipeline_for_image(image_id: uuid.UUID) -> None:
    """
    Run CV and OCR pipeline for a single image in the background.
    """
    async with AsyncSessionLocal() as db:
        img_record = await db.get(Image, image_id)
        if not img_record:
            return

        img_record.preprocessing_status = "PROCESSING"
        await db.commit()

        # Run CV synchronously in an executor
        loop = asyncio.get_running_loop()
        cv_result = await loop.run_in_executor(None, cv_processor.process, img_record.file_path)

        if not cv_result.is_usable:
            img_record.preprocessing_status = "FAILED"
            img_record.ocr_status = "SKIPPED"
            img_record.resolution_width = cv_result.resolution_width
            img_record.resolution_height = cv_result.resolution_height
            img_record.blur_score = cv_result.blur_score
            img_record.glare_score = cv_result.glare_score
            img_record.reflection_score = cv_result.reflection_score
            img_record.orientation_angle = cv_result.orientation_angle
            await db.commit()
            return

        img_record.preprocessing_status = "COMPLETED"
        img_record.resolution_width = cv_result.resolution_width
        img_record.resolution_height = cv_result.resolution_height
        img_record.blur_score = cv_result.blur_score
        img_record.glare_score = cv_result.glare_score
        img_record.reflection_score = cv_result.reflection_score
        img_record.orientation_angle = cv_result.orientation_angle
        img_record.file_path = cv_result.processed_path # Update to processed path
        img_record.ocr_status = "PROCESSING"
        await db.commit()

        # Run OCR synchronously in an executor
        ocr_results_data = await loop.run_in_executor(None, ocr_processor.process, cv_result.processed_path)

        # Save OCR results
        for data in ocr_results_data:
            ocr_record = OcrResult(
                inspection_id=img_record.inspection_id,
                image_id=img_record.id,
                detected_text=data.detected_text,
                bounding_box=data.bounding_box,
                confidence_score=data.confidence_score,
                language=data.language
            )
            db.add(ocr_record)

        img_record.ocr_status = "COMPLETED"
        await db.commit()

        # Check if all images for this inspection are OCR completed
        result = await db.execute(
            select(Image)
            .where(Image.inspection_id == img_record.inspection_id)
        )
        all_images = result.scalars().all()
        
        all_done = all(img.ocr_status in ("COMPLETED", "FAILED", "SKIPPED") for img in all_images)
        if all_done:
             # trigger extraction logic here
             await trigger_extraction(img_record.inspection_id, db)


async def trigger_extraction(inspection_id: uuid.UUID, db: AsyncSession):
    """
    Prototype extraction and rule evaluation logic.
    Extracts basic LMPC fields (MRP, Net Qty) using simple heuristics
    and generates findings based on their presence.
    """
    # 0. Prevent duplicate extraction from race conditions
    existing = await db.execute(select(Finding).where(Finding.inspection_id == inspection_id).limit(1))
    if existing.scalar_one_or_none():
        return
        
    # 1. Fetch OCR results for this inspection
    result = await db.execute(
        select(OcrResult).where(OcrResult.inspection_id == inspection_id)
    )
    ocr_results = result.scalars().all()
    
    full_text = " ".join([ocr.detected_text.lower() for ocr in ocr_results])
    
    fields_to_extract = []
    findings = []
    
    # 2. Heuristic extraction for prototype
    
    # MRP check
    has_mrp = "mrp" in full_text or "rs." in full_text or "rs " in full_text or "₹" in full_text
    if has_mrp:
        fields_to_extract.append(
            ExtractedField(
                inspection_id=inspection_id,
                field_type="MRP",
                raw_value="Found in text",
                is_validated=False
            )
        )
        findings.append(
            Finding(
                inspection_id=inspection_id,
                finding_type="MRP_CHECK",
                status="PASS",
                details={"message": "MRP indicator detected on label"}
            )
        )
    else:
        findings.append(
            Finding(
                inspection_id=inspection_id,
                finding_type="MRP_CHECK",
                status="FAIL",
                details={"message": "No MRP indicator detected on label"}
            )
        )
        
    # Net Quantity check
    has_qty = "net qty" in full_text or "net weight" in full_text or "kg" in full_text or " g " in full_text or "ml" in full_text
    if has_qty:
         fields_to_extract.append(
            ExtractedField(
                inspection_id=inspection_id,
                field_type="NET_QUANTITY",
                raw_value="Found in text",
                is_validated=False
            )
        )
         findings.append(
            Finding(
                inspection_id=inspection_id,
                finding_type="NET_QTY_CHECK",
                status="PASS",
                details={"message": "Net Quantity indicator detected on label"}
            )
        )
    else:
        findings.append(
            Finding(
                inspection_id=inspection_id,
                finding_type="NET_QTY_CHECK",
                status="FAIL",
                details={"message": "No Net Quantity indicator detected on label"}
            )
        )
        
    # 3. Save to DB
    if fields_to_extract:
        db.add_all(fields_to_extract)
    if findings:
        db.add_all(findings)
        
    await db.commit()
