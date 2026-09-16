import re
from typing import Dict, Any, List
from dateutil import parser

def normalize_fields(fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalizes extracted raw values into standard formats and extracts units.
    Updates 'normalized_value' and 'unit' in the dictionaries.
    """
    for field in fields:
        field_type = field["field_type"]
        raw = field["raw_value"]
        
        field["normalized_value"] = raw
        field["unit"] = None
        
        if field_type == "MRP":
            # Extract number
            match = re.search(r'[\d,]+\.?\d*', raw)
            if match:
                val = match.group(0).replace(',', '')
                try:
                    field["normalized_value"] = str(float(val))
                    field["unit"] = "INR"
                except ValueError:
                    pass
                    
        elif field_type == "QUANTITY":
            # Extract number and unit e.g. "500 g", "1.5 kg"
            match = re.search(r'([\d,]+\.?\d*)\s*([a-zA-Z]+)', raw)
            if match:
                val = match.group(1).replace(',', '')
                unit = match.group(2)
                try:
                    field["normalized_value"] = str(float(val))
                    field["unit"] = unit.lower()
                except ValueError:
                    pass
                    
        elif field_type == "DATES":
            # Try to parse date
            # simple cleanup
            cleaned = re.sub(r'[^0-9a-zA-Z/\-.,]', ' ', raw).strip()
            try:
                dt = parser.parse(cleaned, fuzzy=True)
                field["normalized_value"] = dt.strftime("%Y-%m-%d")
            except Exception:
                # If parsing fails, just keep the raw as normalized (or maybe null)
                field["normalized_value"] = cleaned
                
        elif field_type == "CONSUMER_CARE":
            # Extract phone/email
            phone_match = re.search(r'\+?\d{10,13}', raw.replace(' ', '').replace('-', ''))
            email_match = re.search(r'[\w\.-]+@[\w\.-]+', raw)
            
            if email_match:
                field["normalized_value"] = email_match.group(0)
            elif phone_match:
                field["normalized_value"] = phone_match.group(0)
                
    return fields
