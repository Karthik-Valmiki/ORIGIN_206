from typing import Dict, Any, List

def evaluate_check(check: Dict[str, Any], finding: Dict[str, Any], inspection_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates a single rule check against the consolidated finding.
    Returns outcome (PASS, FAIL, AMBIGUOUS) and reason.
    """
    field_type = check.get("field")
    check_type = check.get("type")
    
    if not finding:
        return {"outcome": "AMBIGUOUS", "reason": f"{field_type} not found in findings"}
        
    f_status = finding.get("status")
    f_details = finding.get("details", {})
    
    if check_type == "PRESENCE":
        if f_status == "AMBIGUOUS":
            if f_details.get("not_found"):
                return {"outcome": "AMBIGUOUS", "reason": f"{field_type} not found in any image"}
            return {"outcome": "AMBIGUOUS", "reason": f"{field_type} evidence is ambiguous/insufficient"}
        if f_status == "PASS":
            return {"outcome": "PASS", "reason": f"{field_type} is present"}
        return {"outcome": "FAIL", "reason": f"{field_type} extraction failed"}
        
    if check_type == "UNIT":
        if f_status != "PASS":
            return {"outcome": "AMBIGUOUS", "reason": "Field not reliably extracted for unit check"}
        observed_unit = f_details.get("unit", "")
        if not observed_unit:
            return {"outcome": "FAIL", "reason": "No unit detected"}
        allowed = [u.lower() for u in check.get("allowed_units", [])]
        if observed_unit.lower() in allowed:
            return {"outcome": "PASS", "reason": f"Unit '{observed_unit}' is valid"}
        return {"outcome": "FAIL", "reason": f"Unit '{observed_unit}' not in allowed list"}
        
    if check_type == "VALUE":
        if f_status != "PASS":
            return {"outcome": "AMBIGUOUS", "reason": "Field not reliably extracted for value check"}
        constraint = check.get("constraint")
        if constraint == "NOT_FUTURE":
            observed_date = f_details.get("observed_value")
            insp_date_str = str(inspection_context.get("inspection_date", ""))[:10] # YYYY-MM-DD
            if observed_date and insp_date_str and observed_date > insp_date_str:
                return {"outcome": "FAIL", "reason": f"Date {observed_date} is in the future"}
            return {"outcome": "PASS", "reason": "Date is not in the future"}
            
    # Default for FORMAT, DECLARATION etc
    if f_status == "PASS":
        return {"outcome": "PASS", "reason": f"Satisfied {check_type} check based on presence"}
        
    return {"outcome": "AMBIGUOUS", "reason": f"Could not evaluate check_type: {check_type}"}
