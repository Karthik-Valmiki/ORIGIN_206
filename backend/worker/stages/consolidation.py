from typing import List, Dict, Any

def consolidate_evidence(all_fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Takes all extracted fields across multiple images and consolidates them by field_type.
    Detects conflicts and computes final finding status (PASS, AMBIGUOUS).
    """
    grouped = {}
    for field in all_fields:
        ftype = field["field_type"]
        if ftype not in grouped:
            grouped[ftype] = []
        grouped[ftype].append(field)
        
    consolidated = []
    
    # We must report on all LMPC field types, even if not found
    from ..anchors import ANCHORS
    
    for ftype in ANCHORS.keys():
        if ftype not in grouped:
            consolidated.append({
                "field_type": ftype,
                "status": "AMBIGUOUS",
                "details": {
                    "not_found": True,
                    "conflict": False
                },
                "evidences": []
            })
            continue
            
        group = grouped[ftype]
        
        # Check for conflicts (different normalized values)
        # We ignore cases where one is None and another has value
        valid_vals = [f["normalized_value"] for f in group if f.get("normalized_value")]
        unique_vals = list(set([v.lower() for v in valid_vals]))
        
        has_conflict = len(unique_vals) > 1
        
        if has_conflict:
            consolidated.append({
                "field_type": ftype,
                "status": "AMBIGUOUS",
                "details": {
                    "not_found": False,
                    "conflict": True,
                    "observed_values": unique_vals
                },
                "evidences": group
            })
        else:
            # Pick the one with highest confidence
            best_field = max(group, key=lambda x: x.get("confidence", 0.0))
            
            # If confidence is too low, maybe ambiguous, but we let rule engine decide severity
            # For extraction phase, it's a PASS if we extracted *something* consistently
            consolidated.append({
                "field_type": ftype,
                "status": "PASS",
                "details": {
                    "not_found": False,
                    "conflict": False,
                    "observed_value": best_field.get("normalized_value"),
                    "unit": best_field.get("unit"),
                    "confidence": best_field.get("confidence")
                },
                "evidences": [best_field]
            })
            
    return consolidated
