import sys
import os

# Add the parent directory to sys.path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.rules import LMPCRule
from app.models.product import ProductCategory

def seed_default_rules():
    db = SessionLocal()
    try:
        # Check if a rule already exists
        if db.query(LMPCRule).count() > 0:
            print("Rules already exist.")
            return

        print("Seeding default rule...")
        
        # We will create a generic global rule that applies to ALL categories (category_id = None)
        default_rule = LMPCRule(
            name="Global Default LMPC Rule v1",
            category_id=None,
            version=1,
            status="PUBLISHED",
            rule_data={
                "checks": [
                    {"type": "PRESENCE", "field": "MRP", "required": True},
                    {"type": "PRESENCE", "field": "QUANTITY", "required": True},
                    {"type": "PRESENCE", "field": "MANUFACTURER", "required": True}
                ]
            }
        )
        db.add(default_rule)
        db.commit()
        print("Default published rule created successfully.")
    except Exception as e:
        print(f"Failed to seed rules: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_default_rules()
