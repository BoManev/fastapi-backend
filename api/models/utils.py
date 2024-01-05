from pydantic import field_validator
from sqlalchemy import CheckConstraint
from sqlmodel import SQLModel, Field
import uuid
from datetime import datetime
import io
from typing import BinaryIO, List, Optional, Tuple
from fastapi import UploadFile
from PIL import Image as IMG
from api.utils.faky import Faky


class ImageBase(SQLModel):
    uri: str = Field(nullable=False)
    caption: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    @staticmethod
    def generate(faky: Faky):
        color = (
            faky.fake.random_int(min=0, max=255),
            faky.fake.random_int(min=0, max=255),
            faky.fake.random_int(min=0, max=255),
        )
        img = IMG.new("RGB", (300, 200), color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        return img_bytes

    @staticmethod
    def mocks(faky: Faky, count: int):
        imgs: List[Tuple[str, Tuple[str, io.BytesIO]]] = []
        for x in range(count):
            imgs.append(("files", (f"image{x}.png", ImageBase.generate(faky))))
        return imgs

    @staticmethod
    def to_upload_files(imgs: List[Tuple[str, Tuple[str, BinaryIO]]]):
        files: List[UploadFile] = []
        for _, (filename, img_bytes) in imgs:
            files.append(UploadFile(file=img_bytes, filename=filename))
        return files


class ImageView(SQLModel):
    uri: str
    caption: str | None = None
    created_at: datetime


class RatingBase(SQLModel):
    quality_rating: int = Field(
        nullable=False,
        default=0,
        sa_column_args=(
            CheckConstraint(
                "quality_rating >= 0 AND quality_rating <= 5",
                name="quality_rating_out_of_range",
            )
        ),
    )
    budget_rating: int = Field(
        nullable=False,
        default=0,
        sa_column_args=(
            CheckConstraint(
                "budget_rating >= 0 AND budget_rating <= 5",
                name="budget_rating_out_of_range",
            )
        ),
    )
    on_schedule_rating: int = Field(
        nullable=False,
        default=0,
        sa_column_args=(
            CheckConstraint(
                "on_schedule_rating >= 0 AND on_schedule_rating <= 5",
                name="on_schedule_rating_out_of_range",
            )
        ),
    )

    @field_validator("quality_rating")
    def validate_quality_rating(cls, value):
        if not 0 <= value <= 5:
            raise ValueError("Quality rating must be between 0 and 5.")
        return value

    @field_validator("budget_rating")
    def validate_budget_rating(cls, value):
        if not 0 <= value <= 5:
            raise ValueError("Budget rating must be between 0 and 5.")
        return value

    @field_validator("on_schedule_rating")
    def validate_on_schedule_rating(cls, value):
        if not 0 <= value <= 5:
            raise ValueError("On-schedule rating must be between 0 and 5.")
        return value

    @staticmethod
    def words_quality():
        return {
            "1": "Not Communicative, Very Slow, Rude, Careless, Job Not Done",
            "2": "Barely Communicative, Slow, Disrespectful, Careless, Job Barely Done",
            "3": "Distant, Inefficient, Approachable, Imprecise, Job Half Done",
            "4": "Mostly Communicative, Efficient, Respectful, Careful, Job Mostly Done",
            "5": "Communicative, Efficient, Pleasant, Clean-Cut, Great Job",
        }

    @staticmethod
    def words_budget():
        return {
            "1": "Unfair Price, Low Quality, Horrible Materials, Took Too Long, Unreasonable Rate",
            "2": "High Price, Low Quality, Bad Materials, Took A While, Expensive Rate",
            "3": "Mediocre Price, Mid Quality, Decent Materials, Took Time, Pricey Rate",
            "4": "Good Price, High Quality, Good Materials, Efficient Work, Decent Rate",
            "5": "Fair Price, High Quality, Great Materials, Quick Work, Bargain Rate",
        }

    @staticmethod
    def words_schedule():
        return {
            "1": "Not Punctual, Slow Work, Never On Time, Inaccurate, Not Communicative",
            "2": "Not Punctual, Took A While, Not On Time, Barely Accurate, Barely Communicative",
            "3": "Late, Took Time, Nearly on Time, Decently Accurate, Distant",
            "4": "Mostly Punctual, Efficient Work, Mostly Completed On Time, Accurate, Mostly Communicative",
            "5": "Punctual, Quick Work, Completed On Time, Accurate, Communicative",
        }


class Image(ImageBase):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, unique=True, primary_key=True)


class PortfolioExternalProjectItem(SQLModel):
    id: uuid.UUID
    title: str
    created_at: datetime


class PortfolioExternalProjectsList(SQLModel):
    external_projects: List[PortfolioExternalProjectItem]


class PortfolioPublicProjectItem(SQLModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    completed_at: datetime
    avatar_uri: str
    ratings: RatingBase


class ContractorReviewItem(SQLModel):
    """
    field (pid)
    - The review_id is the same as the project_id
    - 1:1 mapping

    filed (public)
    If this is true you can also query for the public project info
    Otherwise the expanded card view should only include fields from query to
    review info
    """

    bid: uuid.UUID
    title: str
    created_at: datetime
    agg_rating: float
    public: bool
    avatar_uri: str
    professions: List[str]


class ContractorReviewList(SQLModel):
    reviews: List[ContractorReviewItem]


class HomeownerReviewItem(SQLModel):
    bid: uuid.UUID
    title: str
    created_at: datetime
    rating: int
    public: bool
    avatar_uri: str


class HomeownerReviewList(SQLModel):
    reviews: List[HomeownerReviewItem]


class PortfolioPublicProjectsList(SQLModel):
    public_projects: List[PortfolioPublicProjectItem]


class UploadPortfolioView(SQLModel):
    img_uploaded: int
