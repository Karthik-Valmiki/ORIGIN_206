from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.inspection import Inspection, Image, ImageProcessingHistory
from app.models.ocr import OcrResult, ExtractedField
from app.models.findings import Finding, Evidence
import traceback
import sys

# Import stages
try:
    from .stages.image_validation import validate_image
    from .stages.preprocessing import preprocess_image
    from .stages.ocr import run_ocr
    from .stages.field_extraction import extract_fields
    from .stages.normalization import normalize_fields
    from .stages.consolidation import consolidate_evidence
except ImportError:
    print("Warning: CV/OCR dependencies missing. Using mock stages.")
    def validate_image(f): return {"is_valid_file": True, "resolution_width": 1024, "resolution_height": 1024, "blur_score": 1.0, "glare_score": 0.0, "preprocessing_status": "COMPLETED"}
    def preprocess_image(f): return {"success": True, "history": [], "output_path": f}
    def run_ocr(e, f): return [{"detected_text": "MRP Rs 100", "bounding_box": [[0,0],[1,0],[1,1],[0,1]], "confidence_score": 0.99}]
    def extract_fields(ocr_dicts): return []
    def normalize_fields(ext): return ext
    def consolidate_evidence(ext): return []
from .stages.rule_engine import evaluate_check
from .stages.decision_engine import compute_verdict
from .stages.decision_engine import compute_verdict
from .retry import handle_failure

# Global OCR engine initialized by worker main
try:
    from paddleocr import PaddleOCR
except ImportError:
    class PaddleOCR:
        def __init__(self, **kwargs): pass
ocr_engine = None

def get_ocr_engine():
    global ocr_engine
    if ocr_engine is None:
        print("Initializing PaddleOCR engine...")
        ocr_engine = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False)
    return ocr_engine

def process_inspection(inspection_id_str: str, attempt: int = 1):
    db: Session = SessionLocal()
    try:
        inspection = db.query(Inspection).filter(Inspection.id == inspection_id_str).first()
        if not inspection:
            return
            
        # Idempotency check
        if inspection.status in ["COMPLIANT", "NON_COMPLIANT", "REVIEW_REQUIRED", "PROCESSING_FAILED"]:
            return
            
        # Set to PROCESSING
        if inspection.status == "PENDING":
            inspection.status = "PROCESSING"
            db.commit()
            
        images = db.query(Image).filter(Image.inspection_id == inspection.id).all()
        
        all_extracted_fields = []
        
        for img in images:
            # 1. Validation
            val_result = validate_image(img.file_path)
            img.is_valid_file = val_result["is_valid_file"]
            img.resolution_width = val_result["resolution_width"]
            img.resolution_height = val_result["resolution_height"]
            img.blur_score = val_result["blur_score"]
            img.glare_score = val_result["glare_score"]
            img.preprocessing_status = val_result["preprocessing_status"]
            db.commit()
            
            if not img.is_valid_file:
                img.ocr_status = "SKIPPED"
                db.commit()
                continue
                
            # 2. Preprocessing
            img.preprocessing_status = "PROCESSING"
            db.commit()
            
            pre_result = preprocess_image(img.file_path)
            for hist in pre_result["history"]:
                db.add(ImageProcessingHistory(
                    image_id=img.id,
                    step_name=hist["step_name"],
                    status=hist["status"],
                    parameters=hist["parameters"],
                    execution_time_ms=hist["execution_time_ms"]
                ))
                
            if not pre_result["success"]:
                img.preprocessing_status = "FAILED"
                img.ocr_status = "SKIPPED"
                db.commit()
                continue
                
            img.preprocessing_status = "COMPLETED"
            
            # 3. OCR
            img.ocr_status = "PROCESSING"
            db.commit()
            
            engine = get_ocr_engine()
            ocr_res = run_ocr(engine, pre_result["output_path"])
            
            db_ocr_results = []
            for r in ocr_res:
                db_ocr = OcrResult(
                    inspection_id=inspection.id,
                    image_id=img.id,
                    detected_text=r["detected_text"],
                    bounding_box=r["bounding_box"],
                    confidence_score=r["confidence_score"]
                )
                db.add(db_ocr)
                db_ocr_results.append(db_ocr)
                
            db.commit()
            for r in db_ocr_results: db.refresh(r)
            
            img.ocr_status = "COMPLETED"
            db.commit()
            
            # 4. Field Extraction
            # We pass the db_ocr_results as dicts so they have IDs
            ocr_dicts = [{"detected_text": r.detected_text, "bounding_box": r.bounding_box, "confidence_score": r.confidence_score, "id": r.id} for r in db_ocr_results]
            
            extracted = extract_fields(ocr_dicts)
            
            # 5. Normalization
            normalized = normalize_fields(extracted)
            
            for field in normalized:
                db_field = ExtractedField(
                    inspection_id=inspection.id,
                    ocr_result_id=field["ocr_result"]["id"],
                    field_type=field["field_type"],
                    raw_value=field["raw_value"],
                    normalized_value=field["normalized_value"],
                    unit=field["unit"],
                    confidence=field["confidence"]
                )
                db.add(db_field)
                db.commit()
                db.refresh(db_field)
                # Keep the DB ID for consolidation phase
                field["db_id"] = db_field.id
                
            all_extracted_fields.extend(normalized)
            
        # 6. Evidence Consolidation
        consolidated = consolidate_evidence(all_extracted_fields)
        
        for c in consolidated:
            finding = Finding(
                inspection_id=inspection.id,
                finding_type=c["field_type"],
                status=c["status"],
                details=c["details"]
            )
            db.add(finding)
            db.commit()
            db.refresh(finding)
            
            for ev in c["evidences"]:
                db.add(Evidence(
                    inspection_id=inspection.id,
                    finding_id=finding.id,
                    ocr_result_id=ev["ocr_result"]["id"],
                    fusion_confidence=ev["confidence"]
                ))
            db.commit()
            
        # 7. Deterministic Rule Evaluation
        from app.models.rules import LMPCRule
        
        rule = db.query(LMPCRule).filter(LMPCRule.id == inspection.rule_id).first()
        if not rule:
            inspection.status = "PROCESSING_FAILED"
            inspection.notes = f"System Error: Linked rule {inspection.rule_id} not found."
            db.commit()
            return

        # Build finding dict for fast lookup
        finding_dict = {f.finding_type: {"status": f.status, "details": f.details} for f in db.query(Finding).filter(Finding.inspection_id == inspection.id).all()}
        
        inspection_context = {
            "is_imported": inspection.is_imported,
            "inspection_date": inspection.created_at
        }
        
        clause_results = []
        checks = rule.rule_data.get("checks", [])
        for check in checks:
            res = evaluate_check(check, finding_dict.get(check.get("field")), inspection_context)
            clause_results.append(res)
            
        # 9. Decision Engine -> Verdict
        verdict, summary = compute_verdict(clause_results)
        
        inspection.status = verdict
        if inspection.notes:
            inspection.notes += f"\n[VERDICT]: {summary}"
        else:
            inspection.notes = f"[VERDICT]: {summary}"
            
        db.commit()
        
        # Log audit
        from app.services.audit import log_audit_event
        log_audit_event(db, inspection.officer_id, f"PROCESSING_COMPLETED_{verdict}", "inspections", inspection.id, {"summary": summary})
        
    except Exception as e:
        db.rollback()
        print(f"Error in process_inspection: {e}")
        traceback.print_exc()
        
        try:
            # Ensure we mark the inspection as FAILED if any exception crashes the worker
            inspection = db.query(Inspection).filter(Inspection.id == inspection_id_str).first()
            if inspection and inspection.status == "PROCESSING":
                inspection.status = "PROCESSING_FAILED"
                inspection.notes = f"Worker crashed: {str(e)}"
                db.commit()
        except Exception as inner_e:
            print(f"Failed to update inspection status to FAILED: {inner_e}")
            db.rollback()

        if handle_failure(db, inspection_id_str, attempt, str(e)):
            # Requeue for retry
            from app.services.queue import enqueue_inspection_job
            import uuid
            # Not using original enqueue to avoid import loop, just simple retry for prototype
            # Or call process_inspection recursively with attempt+1 after delay
            process_inspection(inspection_id_str, attempt + 1)
            
    finally:
        db.close()
