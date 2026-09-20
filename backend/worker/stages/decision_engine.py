from typing import List, Dict, Any, Tuple

def compute_verdict(clause_results: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Priority order (first match wins):
    1. REVIEW_REQUIRED - any AMBIGUOUS
    2. NON_COMPLIANT   - any FAIL
    3. COMPLIANT       - all PASS
    """
    ambiguous = [r for r in clause_results if r["outcome"] == "AMBIGUOUS"]
    failures = [r for r in clause_results if r["outcome"] == "FAIL"]
    
    if ambiguous:
        return "REVIEW_REQUIRED", f"{len(ambiguous)} clause(s) could not be reliably evaluated"
    if failures:
        return "NON_COMPLIANT", f"{len(failures)} rule clause(s) failed"
    return "COMPLIANT", "All applicable clauses passed"
