from fastapi import APIRouter
from . import auth, users, categories, inspections, images, reviews, reports, audit, admin_ops, rules

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(categories.router)
api_router.include_router(inspections.router)
api_router.include_router(images.router)
api_router.include_router(reviews.router)
api_router.include_router(reports.router)
api_router.include_router(audit.router)
api_router.include_router(admin_ops.router)
api_router.include_router(rules.router)
