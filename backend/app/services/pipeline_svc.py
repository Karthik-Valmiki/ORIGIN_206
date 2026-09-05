"""
Pipeline Service — CV + OCR + Field Extraction + Auto-Verdict.

Flow per image upload:
  1. CV preprocessing (quality gate)
  2. OCR
  3. Field extraction (regex heuristics)
  4. LMPC rule evaluation
  5. auto_verdict() — stamps Inspection.status as COMPLIANT or NON_COMPLIANT
     No human approval step.
"""
import asyncio
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.inspection import (
    Image, Inspection, OcrResult, ExtractedField, Finding
)
from app.pipeline import cv_processor, ocr_processor
from app.database import AsyncSessionLocal


# ══════════════════════════════════════════════════════════════════════════════
#  REQUIRED LMPC FIELDS  (Legal Metrology (Packaged Commodities) Rules, 2011)
# ══════════════════════════════════════════════════════════════════════════════
REQUIRED_FIELDS = {"MRP", "QUANTITY", "MANUFACTURER"}


# ══════════════════════════════════════════════════════════════════════════════
#  STAGE 1 — IMAGE PIPELINE  (CV + OCR)
# ══════════════════════════════════════════════════════════════════════════════

async def run_pipeline_for_image(image_id: uuid.UUID) -> None:
    """
    Background task: runs CV preprocessing + OCR on a single image.
    Once ALL images for the parent inspection are done, triggers
    field extraction and auto-verdict.
    """
    async with AsyncSessionLocal() as db:
        img_record = await db.get(Image, image_id)
        if not img_record:
            return

        # Mark inspection as PROCESSING on first image
        inspection = await db.get(Inspection, img_record.inspection_id)
        if inspection and inspection.status == "PENDING":
            inspection.status = "PROCESSING"
            await db.commit()

        img_record.preprocessing_status = "PROCESSING"
        await db.commit()

        # ── CV preprocessing ───────────────────────────────────────────────
        loop = asyncio.get_running_loop()
        cv_result = await loop.run_in_executor(
            None, cv_processor.process, img_record.file_path
        )

        img_record.resolution_width  = cv_result.resolution_width
        img_record.resolution_height = cv_result.resolution_height
        img_record.blur_score        = cv_result.blur_score
        img_record.glare_score       = cv_result.glare_score
        img_record.reflection_score  = cv_result.reflection_score
        img_record.orientation_angle = cv_result.orientation_angle

        if not cv_result.is_usable:
            img_record.preprocessing_status = "FAILED"
            img_record.ocr_status = "SKIPPED"
            await db.commit()
            # Check if all images are done; verdict still runs
            await _check_and_finalize(img_record.inspection_id, db)
            return

        img_record.preprocessing_status = "COMPLETED"
        img_record.file_path = cv_result.processed_path
        img_record.ocr_status = "PROCESSING"
        await db.commit()

        # ── OCR ───────────────────────────────────────────────────────────
        ocr_data = await loop.run_in_executor(
            None, ocr_processor.process, cv_result.processed_path
        )

        for d in ocr_data:
            db.add(OcrResult(
                inspection_id=img_record.inspection_id,
                image_id=img_record.id,
                detected_text=d.detected_text,
                bounding_box=d.bounding_box,
                confidence_score=d.confidence_score,
                language=d.language,
            ))

        img_record.ocr_status = "COMPLETED"
        await db.commit()

        await _check_and_finalize(img_record.inspection_id, db)


async def _check_and_finalize(inspection_id: uuid.UUID, db: AsyncSession) -> None:
    """
    After each image finishes, check if ALL images for the inspection are done.
    If yes, trigger field extraction + auto-verdict.
    """
    result = await db.execute(
        select(Image).where(Image.inspection_id == inspection_id)
    )
    all_images = result.scalars().all()

    all_done = all(
        img.ocr_status in ("COMPLETED", "FAILED", "SKIPPED")
        for img in all_images
    )
    if all_done:
        await _run_extraction_and_verdict(inspection_id, db)


# ══════════════════════════════════════════════════════════════════════════════
#  STAGE 2 — FIELD EXTRACTION  (regex heuristics from OCR text)
# ══════════════════════════════════════════════════════════════════════════════

async def _run_extraction_and_verdict(inspection_id: uuid.UUID, db: AsyncSession) -> None:
    """
    Idempotent: skips if findings already exist.
    1. Merges OCR text from all images.
    2. Extracts LMPC fields.
    3. Runs auto-verdict and stamps Inspection.status.
    """
    try:
        # Idempotency guard
        existing = await db.execute(
            select(Finding).where(Finding.inspection_id == inspection_id).limit(1)
        )
        if existing.scalar_one_or_none():
            return

        # Fetch all OCR text for this inspection
        result = await db.execute(
            select(OcrResult).where(OcrResult.inspection_id == inspection_id)
        )
        ocr_rows = result.scalars().all()

        full_text      = " ".join(r.detected_text.lower() for r in ocr_rows)
        original_text  = " ".join(r.detected_text         for r in ocr_rows)

        fields: list[ExtractedField] = []
        findings: list[Finding]      = []
        passed_fields: set[str]      = set()

        # ── Rule 1: MRP ────────────────────────────────────────────────────────
        mrp_match = re.search(r'(?:mrp|rs\.?|₹)\s*:?\s*([\d\.,]+)', full_text)
        has_mrp   = bool(mrp_match) or any(kw in full_text for kw in ("mrp", "rs.", "rs ", "₹"))
        mrp_val   = mrp_match.group(1) if mrp_match else None

        if has_mrp:
            fields.append(ExtractedField(
                inspection_id=inspection_id,
                field_type="MRP",
                raw_value=mrp_val or "MRP declaration found",
                normalized_value=mrp_val or "FOUND",
                unit="INR",
                is_validated=True,
            ))
            findings.append(Finding(
                inspection_id=inspection_id,
                finding_type="DECLARATION",
                status="PASS",
                details={
                    "rule": "LMPC Rule 6(1)(e)",
                    "check": "MRP_DECLARATION",
                    "message": "Maximum Retail Price (MRP) declared on label",
                    "extracted": mrp_val or "present",
                },
            ))
            passed_fields.add("MRP")
        else:
            findings.append(Finding(
                inspection_id=inspection_id,
                finding_type="DECLARATION",
                status="FAIL",
                details={
                    "rule": "LMPC Rule 6(1)(e)",
                    "check": "MRP_DECLARATION",
                    "message": "MRP not detected on label — mandatory declaration missing",
                },
            ))

        # ── Rule 2: Net Quantity ───────────────────────────────────────────────
        qty_match = re.search(r'(\d+(?:\.\d+)?)\s*(kg|g|gm|grams|ml|l|litre|liter)', full_text)
        has_qty   = bool(qty_match) or any(kw in full_text for kw in ("net qty", "net weight", "net content"))
        qty_val   = f"{qty_match.group(1)} {qty_match.group(2)}" if qty_match else None

        if has_qty:
            fields.append(ExtractedField(
                inspection_id=inspection_id,
                field_type="QUANTITY",
                raw_value=qty_val or "Net quantity declaration found",
                normalized_value=qty_match.group(1) if qty_match else "FOUND",
                unit=qty_match.group(2) if qty_match else "—",
                is_validated=True,
            ))
            findings.append(Finding(
                inspection_id=inspection_id,
                finding_type="PRESENCE",
                status="PASS",
                details={
                    "rule": "LMPC Rule 6(1)(b)",
                    "check": "NET_QUANTITY",
                    "message": "Net Quantity / Net Content declared on label",
                    "extracted": qty_val or "present",
                },
            ))
            passed_fields.add("QUANTITY")
        else:
            findings.append(Finding(
                inspection_id=inspection_id,
                finding_type="PRESENCE",
                status="FAIL",
                details={
                    "rule": "LMPC Rule 6(1)(b)",
                    "check": "NET_QUANTITY",
                    "message": "Net Quantity not detected on label — mandatory declaration missing",
                },
            ))

        # ── Rule 3: Manufacturer / Marketer Name & Address ─────────────────────
        mfg_keywords = ("manufactured by", "manufactured in", "mfd by", "marketed by",
                        "mkt by", "packed by", "private limited", "pvt. ltd", "ltd.")
        has_mfg = any(kw in full_text for kw in mfg_keywords)

        # Try to extract a recognisable company name token
        mfg_name_match = re.search(
            r'(?:mfd|mkt|marketed|manufactured|packed)\s+by\s+([A-Za-z][^\n,\.]{3,60})',
            original_text, re.IGNORECASE,
        )
        mfg_name = mfg_name_match.group(1).strip() if mfg_name_match else None

        if has_mfg:
            fields.append(ExtractedField(
                inspection_id=inspection_id,
                field_type="MANUFACTURER",
                raw_value=mfg_name or "Manufacturer/Marketer details found",
                normalized_value=mfg_name or "FOUND",
                is_validated=True,
            ))
            findings.append(Finding(
                inspection_id=inspection_id,
                finding_type="DECLARATION",
                status="PASS",
                details={
                    "rule": "LMPC Rule 6(1)(c)",
                    "check": "MANUFACTURER_DECLARATION",
                    "message": "Manufacturer / Marketer name & address declared",
                    "extracted": mfg_name or "present",
                },
            ))
            passed_fields.add("MANUFACTURER")
        else:
            findings.append(Finding(
                inspection_id=inspection_id,
                finding_type="DECLARATION",
                status="FAIL",
                details={
                    "rule": "LMPC Rule 6(1)(c)",
                    "check": "MANUFACTURER_DECLARATION",
                    "message": "Manufacturer/Marketer name & address not detected — mandatory declaration missing",
                },
            ))

        # ── Rule 4: Consumer Care Contact (advisory) ───────────────────────────
        has_care = any(kw in full_text for kw in ("1800", "consumer care", "helpline", "suggestions@", "care@"))
        if has_care:
            care_match = re.search(r'1800[\s\-]?[\d\s\-]+', full_text)
            care_val = care_match.group(0).strip() if care_match else "Consumer care contact found"
            fields.append(ExtractedField(
                inspection_id=inspection_id,
                field_type="CONSUMER_CARE",
                raw_value=care_val,
                normalized_value=re.sub(r'\D', '', care_val) or "FOUND",
                is_validated=True,
            ))
            findings.append(Finding(
                inspection_id=inspection_id,
                finding_type="DECLARATION",
                status="PASS",
                details={
                    "rule": "LMPC Rule 6(1)(g) [advisory]",
                    "check": "CONSUMER_CARE",
                    "message": "Consumer care helpline / email detected",
                    "extracted": care_val,
                },
            ))
        else:
            findings.append(Finding(
                inspection_id=inspection_id,
                finding_type="DECLARATION",
                status="AMBIGUOUS",
                details={
                    "rule": "LMPC Rule 6(1)(g) [advisory]",
                    "check": "CONSUMER_CARE",
                    "message": "Consumer care contact not detected (recommended but not always mandatory)",
                },
            ))

        # ── Rule 5: Date of Manufacture / Packing ─────────────────────────────
        date_patterns = [
            r'\b\d{2}[\/\-]\d{4}\b',          # MM/YYYY
            r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-\.]?\d{4}\b',
            r'\bpkd\b', r'\bmfd\b', r'\bbest before\b', r'\buse by\b',
        ]
        has_dates = any(re.search(p, full_text) for p in date_patterns) or \
                    any(kw in full_text for kw in ("date of mfg", "manufacturing date", "expiry", "exp."))

        if has_dates:
            date_match = re.search(r'\b\d{2}[\/\-]\d{4}\b', full_text)
            date_val = date_match.group(0) if date_match else "Date declaration found"
            fields.append(ExtractedField(
                inspection_id=inspection_id,
                field_type="DATES",
                raw_value=date_val,
                normalized_value=date_val,
                is_validated=True,
            ))
            findings.append(Finding(
                inspection_id=inspection_id,
                finding_type="FORMAT",
                status="PASS",
                details={
                    "rule": "LMPC Rule 6(1)(d)",
                    "check": "DATE_DECLARATION",
                    "message": "Date of Manufacture / Packing detected",
                    "extracted": date_val,
                },
            ))
        else:
            findings.append(Finding(
                inspection_id=inspection_id,
                finding_type="FORMAT",
                status="FAIL",
                details={
                    "rule": "LMPC Rule 6(1)(d)",
                    "check": "DATE_DECLARATION",
                    "message": "Date of Manufacture / Packing not detected on label",
                },
            ))

        # ── Save fields + findings ─────────────────────────────────────────────
        if fields:
            db.add_all(fields)
        if findings:
            db.add_all(findings)
        await db.commit()

        # ── Stage 3: Auto-verdict ──────────────────────────────────────────────
        await _auto_verdict(inspection_id, passed_fields, db)
    except Exception as exc:
        print(f"Error in _run_extraction_and_verdict: {exc}", flush=True)
        try:
            inspection = await db.get(Inspection, inspection_id)
            if inspection:
                inspection.status = "PROCESSING_FAILED"
                await db.commit()
        except Exception:
            pass
        raise


# ══════════════════════════════════════════════════════════════════════════════
#  STAGE 3 — AUTO VERDICT
# ══════════════════════════════════════════════════════════════════════════════

async def _auto_verdict(
    inspection_id: uuid.UUID,
    passed_fields: set[str],
    db: AsyncSession,
) -> None:
    """
    Compares passed_fields against active mandatory rules in the database.
    Falls back to REQUIRED_FIELDS if no active rules are defined.
    Sets Inspection.status to COMPLIANT or NON_COMPLIANT automatically.
    No human approval step.
    """
    inspection = await db.get(Inspection, inspection_id)
    if not inspection:
        return

    # Dynamically query mandatory fields from the active rule version
    required = set()
    try:
        from app.models.inspection import RuleVersion, Rule
        res = await db.execute(
            select(Rule)
            .join(RuleVersion, Rule.rule_version_id == RuleVersion.id)
            .where(RuleVersion.is_active.is_(True))
        )
        active_rules = res.scalars().all()
        for r in active_rules:
            params = r.parameters or {}
            if params.get("is_mandatory") is True and params.get("field"):
                required.add(params["field"].upper().strip())
    except Exception as e:
        print(f"Warning: could not query active rules dynamically ({e}), using default", flush=True)

    if not required:
        required = set(REQUIRED_FIELDS)

    missing = required - passed_fields

    if not missing:
        inspection.status = "COMPLIANT"
    else:
        inspection.status = "NON_COMPLIANT"

    await db.commit()
