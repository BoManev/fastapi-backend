from fastapi import APIRouter
from api.config import get_config

from api.route.contractor import router as contractor
from api.route.homeowner import router as homeowner
from api.route.root import router as root


config = get_config()
api = APIRouter(prefix=config.ROOT_PATH)

api.include_router(root, prefix="", tags=["Utility"])
api.include_router(contractor, prefix="/contractor", tags=["Contractor"])
api.include_router(homeowner, prefix="/homeowner", tags=["Homeowner"])
