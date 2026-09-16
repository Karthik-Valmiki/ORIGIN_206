from sqlalchemy.orm import Session
from .models.rbac import Role, Permission, RolePermission, User, UserRole
from .models.product import ProductCategory
from .core.security import get_password_hash
from .models.rules import LMPCRule

SEED_CATEGORIES = [
    {"category_name": "GENERAL_PACKAGED_COMMODITY",  "description": "Default. General pre-packaged commodities under LMPC 2011."},
    {"category_name": "PACKAGED_FOOD",               "description": "Food products. FSSAI license + expiry rules apply."},
    {"category_name": "COSMETICS_AND_PERSONAL_CARE", "description": "Cosmetics, toiletries, personal care. Expiry rules apply."},
    {"category_name": "ELECTRONICS_AND_ELECTRICAL",   "description": "Electronic and electrical appliances. BIS certification."},
    {"category_name": "PHARMACEUTICALS",              "description": "Pharmaceutical and medicinal products. Drug rules + expiry."},
    {"category_name": "TEXTILE_AND_GARMENTS",         "description": "Textiles, garments, and fabric products."},
]

def seed_database(db: Session):
    # 1. Seed Roles
    admin_role = db.query(Role).filter(Role.role_name == "ADMIN").first()
    if not admin_role:
        admin_role = Role(role_name="ADMIN", description="Administrator with full access")
        db.add(admin_role)
    
    officer_role = db.query(Role).filter(Role.role_name == "OFFICER").first()
    if not officer_role:
        officer_role = Role(role_name="OFFICER", description="Field officer who conducts inspections")
        db.add(officer_role)
        
    db.commit()
    db.refresh(admin_role)
    db.refresh(officer_role)
    
    # 2. Seed Admin User
    admin_user = db.query(User).filter(User.email == "admin@sih26034.gov.in").first()
    if not admin_user:
        admin_user = User(
            full_name="System Administrator",
            email="admin@sih26034.gov.in",
            password_hash=get_password_hash("Admin@123")
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        # Assign ADMIN role
        user_role = UserRole(user_id=admin_user.id, role_id=admin_role.id)
        db.add(user_role)
        db.commit()
        
    # 3. Seed Categories
    for cat_data in SEED_CATEGORIES:
        category = db.query(ProductCategory).filter(ProductCategory.category_name == cat_data["category_name"]).first()
        if not category:
            category = ProductCategory(**cat_data)
            db.add(category)
    
    # 4. Seed Default Rule
    if db.query(LMPCRule).count() == 0:
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
    print("Database seeding completed.")
