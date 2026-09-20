from sqlalchemy.orm import Session
from ...app.models.rules import RuleApplicability, RuleVersion
from ...app.models.inspection import Inspection
from datetime import datetime
import uuid

def select_rule_version(db: Session, inspection: Inspection) -> str:
    """
    Selects the applicable rule version based on category, imported status, and current date.
    Returns the rule_version_id or raises an exception.
    """
    now = datetime.utcnow()
    applicabilities = db.query(RuleApplicability).filter(
        RuleApplicability.product_category_id == inspection.product_category_id,
        RuleApplicability.is_imported == inspection.is_imported,
        RuleApplicability.effective_from <= now,
        (RuleApplicability.effective_until >= now) | (RuleApplicability.effective_until.is_(None))
    ).all()
    
    # We must find exactly one active rule version
    valid_versions = []
    for app in applicabilities:
        version = db.query(RuleVersion).filter(RuleVersion.id == app.rule_version_id, RuleVersion.is_active == True).first()
        if version:
            valid_versions.append(version)
            
    if len(valid_versions) == 0:
        # Fallback to the rule_version_id already attached to the inspection if it was pre-selected
        if inspection.rule_version_id:
            version = db.query(RuleVersion).filter(RuleVersion.id == inspection.rule_version_id, RuleVersion.is_active == True).first()
            if version:
                return str(version.id)
        raise ValueError("No applicable active rule version found for this category and context.")
        
    if len(valid_versions) > 1:
        raise ValueError("Multiple overlapping rule versions found. Configuration error.")
        
    return str(valid_versions[0].id)
