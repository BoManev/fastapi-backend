from typing import List
from fastapi import APIRouter
from api import models
from api.config import SessionConfig, get_config
from api.core.auth.auth import PasswordAuthUser, TokenAuthUser
from api.core.auth.utils import Token, create_access_token
from api.core.db import SessionDB

router = APIRouter()

config = get_config()


@router.get("/health")
def health():
    # TODO: event driven arch
    # dispatch("demo_contractors", payload={"bid": ...})
    return {"status": "ok"}


@router.get("/isAtuh")
def is_auth(user: TokenAuthUser):
    return {"status": "ok"}


@router.post("/token", response_model=Token)
def token(user: PasswordAuthUser, config: SessionConfig):
    access_token = create_access_token(
        {"sub": user.email, "id": user.id.urn, "scopes": user.role}, config
    )
    return {"access_token": access_token, "token_type": f"bearer scope={user.role}"}


@router.get("/quiz")
def quiz(_user: TokenAuthUser, db: SessionDB):
    """
    Return a JSON encoded string with the schema for the booking quiz
    area:room:category:subcategory:subcategory_idx:
    work_unit_idx:
    - quantity:
    - action:
    - profession:

    Example:
    "Indoors:Living Room:Furniture:Couches:0
    1:
    - quantity: "Count"
    - action: "Repair"
    - profession: "Furniture Repair Specialist"
    """
    return models.WorkUnitView.to_json(db)


@router.get("/professions", response_model=List[str])
def list_professions(_user: TokenAuthUser, db: SessionDB):
    """
    Get a list of available professions

    Usage: Initial profession selection when new contractor signs up
    """
    units = models.WorkUnit.all_professions(db)
    return [unit[0] for unit in units]


@router.get("/review_words")
def review_words(_user: TokenAuthUser):
    """
    Get a list of words used during the review flow at the end of a project

    Note: To leave a review, project completion must have been singaled by the
    contractor
    """
    return {
        "quality": models.RatingBase.words_quality(),
        "on_schedule": models.RatingBase.words_schedule(),
        "budget": models.RatingBase.words_budget(),
    }
