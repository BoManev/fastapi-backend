from datetime import datetime
import enum
import random
import uuid
from pydantic import condecimal
from sqlalchemy import TIMESTAMP, UUID, Column, ForeignKey, and_, func
from sqlmodel import Field, SQLModel, Session, select
from typing import List

from api.models.booking import (
    BookingDetail,
    BookingInvite,
    BookingUnit,
    BookingUnitView,
)
from api.models.quiz.model import WorkUnit
from api.utils.faky import Faky


class MaterialUnitCreate(SQLModel):
    cost: condecimal(max_digits=8, decimal_places=3) | None = None
    description: str


class QuoteItemCreate(SQLModel):
    booking_unit_id: uuid.UUID
    work_hours: condecimal(max_digits=8, decimal_places=3) | None = None
    work_rate: condecimal(max_digits=8, decimal_places=3) | None = None
    work_cost: condecimal(max_digits=8, decimal_places=3) | None = None
    description: str | None = None
    materials: List[MaterialUnitCreate] | None = None


class QuoteItemStatus(str, enum.Enum):
    ongoing = "ongoing"
    delayed = "delayed"
    completed = "completed"


class QuoteItemUpdate(SQLModel):
    status: QuoteItemStatus


class QuoteItem(SQLModel, table=True):
    __tablename__ = "quote_items"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    qoute_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("quotes.id", initially="DEFERRED", deferrable=True),
            nullable=False,
        )
    )
    booking_unit_id: uuid.UUID = Field(foreign_key="booking_units.id", nullable=False)

    work_hours: condecimal(max_digits=8, decimal_places=3) | None = Field(nullable=True)
    work_rate: condecimal(max_digits=8, decimal_places=3) | None = Field(nullable=True)
    work_cost: condecimal(max_digits=8, decimal_places=3) | None = Field(nullable=True)

    description: str = Field(nullable=True)

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    modified_at: datetime = Field(
        sa_column=Column(TIMESTAMP, default=datetime.utcnow, onupdate=func.now())
    )

    status: str = Field(default=QuoteItemStatus.ongoing, nullable=False)
    is_active: bool = Field(default=True, nullable=False)

    @staticmethod
    def by_qiid(qiid: uuid.UUID, bid: uuid.UUID, db: Session):
        return db.exec(
            select(QuoteItem)
            .join(Quote, and_(Quote.booking_id == bid, Quote.accepted == True))
            .where(and_(QuoteItem.id == qiid, QuoteItem.qoute_id == Quote.id))
        ).first()


class MaterialUnit(SQLModel, table=True):
    __tablename__ = "material_units"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    quote_item_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("quote_items.id", initially="DEFERRED", deferrable=True),
            nullable=False,
        )
    )
    cost: condecimal(max_digits=8, decimal_places=3) = Field(nullable=True)
    description: str = Field(nullable=True)


class QuoteCreate(SQLModel):
    items: List[QuoteItemCreate]

    @staticmethod
    def mock(faky: Faky, bid: uuid.UUID, cid: uuid.UUID, db: Session):
        booking = BookingDetail.by_bid_with_units_is_booked(bid, db)
        items = [
            QuoteItemCreate(
                booking_unit_id=unit.get("booking_unit_id", None),
                description=faky.fake.word(),
                work_rate=random.randint(0, 100),
                work_hours=random.randint(0, 100),
                materials=[
                    MaterialUnitCreate(
                        cost=random.randint(0, 100), description=faky.fake.word()
                    )
                ],
            )
            for unit in booking[1]
        ]
        return QuoteCreate(items=items)


class Quote(SQLModel, table=True):
    __tablename__ = "quotes"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    booking_id: uuid.UUID = Field(foreign_key="bookings.id", nullable=False)
    booking_invite_id: uuid.UUID = Field(
        foreign_key="booking_invites.id", nullable=False
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    accepted: bool = Field(default=False, nullable=False)

    @staticmethod
    def create(quote: QuoteCreate, bid: uuid.UUID, biid: uuid.UUID, db: Session):
        model = Quote(booking_id=bid, booking_invite_id=biid)
        db.add(model)
        for item in quote.items:
            print(item)
            materials = item.model_dump().pop("materials", None)
            # print(item.work_rate, item.work_hours, item.work_cost)
            # if (item.work_rate != None and item.work_hours != None)
            # match (item.work_rate, item.work_hours, item.work_cost):
            #     case None, _, None:
            #         item.work_hours = item.work_cost / item.work_rate
            #     case _, None, None:
            #         item.work_rate = item.work_cost / item.work_hours
            #     case _, _, None:
            #         item.work_cost = item.work_rate * item.work_hours
            #     case None, None, None:
            #         return "not provided pricing for quote item"
            #     # case _, _, _:
            #     #     if item.work_cost != item.work_rate * item.work_hours:
            #     #         return "total cost not matching rate and hours"

            quote_item = QuoteItem(qoute_id=model.id, **item.model_dump())
            db.add_all(
                [
                    MaterialUnit(**material, quote_item_id=quote_item.id)
                    for material in materials
                ]
            )
            db.add(quote_item)

    @staticmethod
    def by_bid(bid: uuid.UUID, cid: uuid.UUID, db: Session):
        return db.exec(
            select(Quote)
            .join(BookingInvite, BookingInvite.contractor_id == cid)
            .where(
                and_(
                    Quote.booking_id == bid, Quote.booking_invite_id == BookingInvite.id
                )
            )
        ).first()

    @staticmethod
    def by_cid(bid: uuid.UUID, cid: uuid.UUID, db: Session):
        qid = Quote.id.label("qid")
        biid = BookingInvite.id.label("biid")
        invite_q = (
            select(qid, biid)
            .where(BookingInvite.contractor_id == cid)
            .join(
                Quote,
                and_(
                    Quote.booking_id == bid, Quote.booking_invite_id == BookingInvite.id
                ),
            )
            .cte("invite_q")
        )

        model = db.exec(
            select(
                Quote,
                func.array_agg(
                    func.jsonb_build_object(
                        "booking_unit",
                        func.jsonb_build_object(
                            "booking_unit_id",
                            BookingUnit.id,
                            "work_unit_id",
                            BookingUnit.work_unit_id,
                            "description",
                            BookingUnit.description,
                            "quantity",
                            BookingUnit.quantity,
                            "work_unit",
                            func.concat(
                                WorkUnit.area,
                                ":",
                                WorkUnit.location,
                                ":",
                                WorkUnit.category,
                                ":",
                                WorkUnit.subcategory,
                                ":",
                                WorkUnit.action,
                            ),
                        ),
                        "quote_item",
                        func.to_jsonb(QuoteItem.__table__.table_valued()),
                        "material_unit",
                        func.to_jsonb(MaterialUnit.__table__.table_valued()),
                    ),
                ),
            )
            .where(Quote.id == invite_q.c.qid)
            .join(
                BookingUnit,
                BookingUnit.booking_id == bid,
            )
            .join(
                QuoteItem,
                and_(
                    QuoteItem.booking_unit_id == BookingUnit.id,
                    QuoteItem.qoute_id == Quote.id,
                ),
            )
            .join(WorkUnit, WorkUnit.id == BookingUnit.work_unit_id)
            .join(MaterialUnit, MaterialUnit.quote_item_id == QuoteItem.id)
            .group_by(Quote)
            .distinct()
        ).first()
        return model


class MaterialView(SQLModel):
    cost: condecimal(max_digits=8, decimal_places=3)
    description: str


class QuoteItemView(SQLModel):
    id: uuid.UUID
    work_rate: condecimal(max_digits=8, decimal_places=3) | None = None
    work_hours: condecimal(max_digits=8, decimal_places=3) | None = None
    work_cost: condecimal(max_digits=8, decimal_places=3) | None = None
    description: str | None = None

    created_at: datetime
    modified_at: datetime

    status: QuoteItemStatus
    is_active: bool
    # TODO: make this a list
    material_unit: MaterialView
    booking_unit: BookingUnitView


class QuoteView(SQLModel):
    items: List[QuoteItemView]
    created_at: datetime
    accepted: bool
