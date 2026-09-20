from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.rbac import User
from ..models.rules import LMPCRule
from ..models.product import ProductCategory
from ..schemas.rules import LMPCRuleCreate, LMPCRuleOut, RuleValidationResult
from ..core.dependencies import require_admin
from ..services.audit import log_audit_event
import uuid

router = APIRouter(prefix="/admin/rules", tags=["Rule Administration"])

@router.get("", response_model=dict)
def list_rules(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    rules = db.query(LMPCRule).order_by(LMPCRule.created_at.desc()).offset(skip).limit(limit).all()
    total = db.query(LMPCRule).count()
    
    result = []
    for r in rules:
        r_dict = LMPCRuleOut.model_validate(r).model_dump()
        if r.category_id:
            cat = db.query(ProductCategory).filter(ProductCategory.id == r.category_id).first()
            if cat:
                r_dict["category_name"] = cat.name
        result.append(r_dict)
        
    return {"data": result, "total": total}

@router.get("/{rule_id}", response_model=LMPCRuleOut)
def get_rule(rule_id: uuid.UUID, db: Session = Depends(get_db)):
    rule = db.query(LMPCRule).filter(LMPCRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

@router.post("", response_model=LMPCRuleOut)
def create_rule(
    rule_in: LMPCRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    # Check if we are updating an existing rule (creating a new version)
    existing = db.query(LMPCRule).filter(LMPCRule.name == rule_in.name).order_by(LMPCRule.version.desc()).first()
    version = existing.version + 1 if existing else 1
    
    rule = LMPCRule(
        name=rule_in.name,
        category_id=rule_in.category_id,
        rule_data=rule_in.rule_data,
        effective_from=rule_in.effective_from,
        version=version,
        status="DRAFT"
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    log_audit_event(db, current_user.id, "CREATE_RULE", "lmpc_rules", rule.id)
    return rule

@router.post("/validate", response_model=RuleValidationResult)
def validate_rule(rule_in: dict, current_user: User = Depends(require_admin)):
    # Basic validation of the rule JSON structure
    errors = []
    rule_data = rule_in.get("rule_data", {})
    if not isinstance(rule_data, dict):
        errors.append("rule_data must be an object")
    elif "clauses" not in rule_data:
        errors.append("rule_data must contain a 'clauses' array")
    elif not isinstance(rule_data["clauses"], list):
        errors.append("'clauses' must be an array")
        
    return {"valid": len(errors) == 0, "errors": errors if errors else None}

@router.post("/{rule_id}/publish", response_model=LMPCRuleOut)
def publish_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    rule = db.query(LMPCRule).filter(LMPCRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
        
    rule.status = "PUBLISHED"
    db.commit()
    db.refresh(rule)
    
    log_audit_event(db, current_user.id, "PUBLISH_RULE", "lmpc_rules", rule.id)
    return rule
