from datetime import datetime
import random
from typing import List
import uuid
from sqlalchemy import UUID, CheckConstraint, Column, ForeignKey, and_, func

from sqlmodel import Field, SQLModel, Session, select
from api.models.booking import BookingDetail, BookingUnit
from api.models.contractor import Contractor, ContractorAnalytics, ContractorRating
from api.models.homeowner import Homeowner
from api.models.project import Project
from api.models.quiz.model import WorkUnit
from api.utils.faky import Faky


class ContractorReviewCreate(ContractorRating):
    is_project_public: bool | None = None
    description: str | None = None
    budget_words: List[str] = []
    quality_words: List[str] = []
    schedule_words: List[str] = []

    @staticmethod
    def mock(faky: Faky):
        quality_rating = faky.rating()
        budget_rating = faky.rating()
        on_schedule_rating = faky.rating()
        return ContractorReviewCreate(
            quality_rating=quality_rating,
            budget_rating=budget_rating,
            on_schedule_rating=on_schedule_rating,
            budget_words=[
                random.choice(ContractorRating.words_budget().get(str(budget_rating)).split(", "))
            ],
            quality_words=[
                random.choice(ContractorRating.words_budget().get(str(quality_rating)).split(", "))
            ],
            schedule_words=[
                random.choice(
                    ContractorRating.words_budget().get(str(on_schedule_rating)).split(", ")
                )
            ],
            description=faky.fake.word(),
        )


class ContractorReview(ContractorRating, table=True):
    __tablename__ = "contractor_reviews"

    booking_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("projects.booking_id", initially="DEFERRED", deferrable=True),
            primary_key=True,
        )
    )
    to_: uuid.UUID = Field(foreign_key="contractors.id", primary_key=True)
    from_: uuid.UUID = Field(foreign_key="homeowners.id", primary_key=True)
    # comma seperated words
    budget_words: str | None = Field(nullable=True)
    quality_words: str | None = Field(nullable=True)
    schedule_words: str | None = Field(nullable=True)
    description: str | None = Field(nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    @staticmethod
    def create(
        review: ContractorReviewCreate,
        to_: uuid.UUID,
        from_: uuid.UUID,
        pid: uuid.UUID,
        db: Session,
    ):
        analytics = ContractorAnalytics.by_cid(to_, db)
        cnt = Contractor.by_cid(to_, db)
        if analytics.reviews == 0:
            cnt[0].quality_rating = review.quality_rating
            cnt[0].budget_rating = review.budget_rating
            cnt[0].on_schedule_rating = review.on_schedule_rating
        else: 
            cnt[0].quality_rating = (cnt[0].quality_rating + review.quality_rating) / 2
            cnt[0].budget_rating = (cnt[0].budget_rating + review.budget_rating) / 2
            cnt[0].on_schedule_rating = (cnt[0].on_schedule_rating + review.on_schedule_rating) / 2
        analytics.reviews += 1
        analytics.completed_projects += 1
        model = ContractorReview(
            quality_rating=review.quality_rating,
            budget_rating=review.budget_rating,
            on_schedule_rating=review.on_schedule_rating,
            quality_words=",".join(review.quality_words),
            budget_words=",".join(review.budget_words),
            schedule_words=",".join(review.schedule_words),
            to_=to_,
            from_=from_,
            booking_id=pid,
            description=review.description,
        )
        db.add(model)
        db.add(analytics)
        db.add(cnt[0])
        return model

    @staticmethod
    def all_by_cid(cid: uuid.UUID, db: Session):
        query = (
            select(
                ContractorReview.booking_id,
                ContractorReview.budget_rating,
                ContractorReview.quality_rating,
                ContractorReview.on_schedule_rating,
                ContractorReview.created_at,
                Project.is_public,
                BookingDetail.title,
                Homeowner.avatar_uri,
                func.array_agg(WorkUnit.profession.distinct()),
            )
            .where(ContractorReview.to_ == cid)
            .join(Project, Project.booking_id == ContractorReview.booking_id)
            .join(BookingDetail, BookingDetail.id == Project.booking_id)
            .join(Homeowner, Homeowner.id == BookingDetail.homeowner_id)
            .join(BookingUnit, BookingUnit.booking_id == BookingDetail.id)
            .join(WorkUnit, WorkUnit.id == BookingUnit.work_unit_id)
            .group_by(ContractorReview, Project, BookingDetail, Homeowner)
        )
        reviews = db.exec(query).all()
        return reviews

    @staticmethod
    def public_list_by_cid(cid: uuid.UUID, db: Session):
        query = (
            select(
                Project.booking_id,
                Project.created_at,
                Project.completed_at,
                BookingDetail.title,
                Homeowner.avatar_uri,
                func.json_build_object(
                    "quality_rating",
                    ContractorReview.quality_rating,
                    "on_schedule_rating",
                    ContractorReview.on_schedule_rating,
                    "budget_rating",
                    ContractorReview.budget_rating,
                ),
            )
            .where(
                and_(
                    Project.contractor_id == cid,
                    Project.is_active == False,
                    Project.is_public == True,
                )
            )
            .join(BookingDetail, BookingDetail.id == Project.booking_id)
            .join(Homeowner, Homeowner.id == BookingDetail.homeowner_id)
            .outerjoin(
                ContractorReview,
                and_(
                    ContractorReview.to_ == cid,
                    ContractorReview.booking_id == Project.booking_id,
                ),
            )
        )
        models = db.execute(query).all()
        return models

    # @staticmethod
    # def all_by_cid(cid: uuid.UUID, db: Session):
    #     query = (
    #         select(
    #             ContractorReview.project_id,
    #             ContractorReview.budget_rating,
    #             ContractorReview.quality_rating,
    #             ContractorReview.on_schedule_rating,
    #             ContractorReview.created_at,
    #             Project.is_public,
    #             BookingDetail.title,
    #             Homeowner.avatar_uri,
    #             func.json_agg(
    #                 func.json_build_object(
    #                     "work_unit_id",
    #                     BookingUnit.work_unit_id,
    #                     "work_unit",
    #                     func.concat(
    #                         WorkUnit.area,
    #                         ":",
    #                         WorkUnit.location,
    #                         ":",
    #                         WorkUnit.category,
    #                         ":",
    #                         WorkUnit.subcategory,
    #                         ":",
    #                         WorkUnit.action,
    #                     ),
    #                 )
    #             ),
    #             func.array_agg(WorkUnit.profession),
    #         )
    #         .where(ContractorReview.to_ == cid)
    #         .join(Project, Project.id == ContractorReview.project_id)
    #         .join(BookingDetail, BookingDetail.id == Project.booking_id)
    #         .join(Homeowner, Homeowner.id == BookingDetail.homeowner_id)
    #         .join(BookingUnit, BookingUnit.booking_id == BookingDetail.id)
    #         .join(WorkUnit, WorkUnit.id == BookingUnit.work_unit_id)
    #         .group_by(ContractorReview, Project, BookingDetail, Homeowner)
    #     )
    #     contractor = db.exec(query).all()
    #     return contractor

    @staticmethod
    def by_bid(bid: uuid.UUID, db: Session):
        query = (
            select(ContractorReview, Project.is_public)
            .where(ContractorReview.booking_id == bid)
            .join(Project, Project.booking_id == ContractorReview.booking_id)
        )
        review = db.exec(query).first()
        return review


class ContractorReviewView(ContractorRating):
    public: bool = False
    booking_id: uuid.UUID
    to_: uuid.UUID
    from_: uuid.UUID
    budget_words: List[str] | None = None
    quality_words: List[str] | None = None
    schedule_words: List[str] | None = None
    description: str | None = None
    created_at: datetime


class HomeownerReviewCreate(SQLModel):
    # TODO: switch to floats and use pydantic to validate [0, 5]
    rating: int
    rating_words: List[str] = []
    description: str | None = None

    @staticmethod
    def words():
        return {
            "1": "Rude, Unfair Price, Inaccurate, Not Communicative, Doesn't Cooperate",
            "2": "Disrespectful, Bad Price, Barely Accurate, Barely Communicative, Unreasonable",
            "3": "Approachable, Mediocre Price, Decently Accurate, Distant, Hard To Reason",
            "4": "Respectful, Good Price, Mostly Accurate, Mostly Communicative, Good Listener",
            "5": "Pleasant, Great Price, Accurate, Communicative, Reasonable",
        }

    @staticmethod
    def mock(faky: Faky):
        rating = faky.rating()
        return HomeownerReviewCreate(
            rating=rating,
            rating_words=[
                random.choice(HomeownerReviewCreate.words().get(str(rating)).split(", "))
            ],
            description=faky.fake.word(),
        )


class HomeownerReview(SQLModel, table=True):
    __tablename__ = "homeowner_reviews"

    booking_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("projects.booking_id", initially="DEFERRED", deferrable=True),
            primary_key=True,
        )
    )
    to_: uuid.UUID = Field(foreign_key="homeowners.id", primary_key=True)
    from_: uuid.UUID = Field(foreign_key="contractors.id", primary_key=True)
    rating_words: str | None = Field(nullable=True)
    rating: int = Field(
        nullable=False,
        default=0,
        sa_column_args=(
            CheckConstraint(
                "quality_rating >= 0 AND quality_rating <= 5",
                name="quality_rating_out_of_range",
            )
        ),
    )
    description: str | None = Field(nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    @staticmethod
    def create(
        review: HomeownerReviewCreate,
        to_: uuid.UUID,
        from_: uuid.UUID,
        bid: uuid.UUID,
        db: Session,
    ):
        # TODO: add hmw analytics
        hmw = Homeowner.by_hid(to_, db)
        hmw.rating = (hmw.rating + review.rating) / 2

        model = HomeownerReview(
            rating=review.rating,
            rating_words=",".join(review.rating_words),
            to_=to_,
            from_=from_,
            booking_id=bid,
            description=review.description,
        )
        db.add(model)
        db.add(hmw)
        return model

    @staticmethod
    def all_by_hid(hid: uuid.UUID, db: Session):
        query = (
            select(
                HomeownerReview.booking_id,
                HomeownerReview.rating,
                HomeownerReview.created_at,
                Project.is_public,
                BookingDetail.title,
                Contractor.avatar_uri,
            )
            .where(HomeownerReview.to_ == hid)
            .join(Project, Project.booking_id == HomeownerReview.booking_id)
            .join(BookingDetail, BookingDetail.id == Project.booking_id)
            .join(Contractor, Contractor.id == Project.contractor_id)
            .join(BookingUnit, BookingUnit.booking_id == BookingDetail.id)
            .group_by(HomeownerReview, Project, BookingDetail, Contractor)
        )
        reviews = db.exec(query).all()
        return reviews

    @staticmethod
    def by_bid(bid: uuid.UUID, db: Session):
        query = (
            select(HomeownerReview, Project.is_public)
            .where(HomeownerReview.booking_id == bid)
            .join(Project, Project.booking_id == HomeownerReview.booking_id)
        )
        review = db.exec(query).first()
        return review

    @staticmethod
    def with_booking(bid: uuid.UUID, db: Session):
        query = (
            select(BookingDetail.homeowner_id, HomeownerReview)
            .where(and_(BookingDetail.id == bid, BookingDetail.is_booked == True))
            .outerjoin(HomeownerReview, HomeownerReview.booking_id == BookingDetail.id)
        )
        model = db.exec(query).first()
        return model


class HomeownerReviewView(SQLModel):
    public: bool = False
    booking_id: uuid.UUID
    to_: uuid.UUID
    from_: uuid.UUID
    rating_words: List[str] | None = None
    rating: int
    description: str | None = None
    created_at: datetime
