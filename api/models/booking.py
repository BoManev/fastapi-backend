from datetime import datetime
import json
import os
from posixpath import splitext
from typing import Annotated, List, Optional
import uuid
from fastapi import Form
from pydantic import TypeAdapter
from sqlalchemy import (
    UUID,
    Column,
    ForeignKey,
    and_,
    func,
)
from sqlmodel import SQLModel, Session, select, Field
from api.config import get_config
from api.core.error import APIError
from api.models.contractor import (
    Contractor,
    ContractorAreaPreference,
    ContractorPreferencesCreate,
    ContractorPublicView,
    ContractorUnitPreference,
)
from api.models.homeowner import Homeowner, HomeownerPublicView
from api.models.quiz.model import WorkUnit
from api.models.utils import Image, ImageView
from api.utils.faky import Faky


class BookingImage(Image, table=True):
    __tablename__ = "booking_images"

    booking_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("bookings.id", initially="DEFERRED", deferrable=True),
            nullable=False,
        )
    )

    @staticmethod
    def all_by_bid(bid: uuid.UUID, db: Session):
        query = select(BookingImage).where(BookingImage.booking_id == bid)
        images = db.exec(query).all()
        return images

    @staticmethod
    def upload_dir():
        upload_dir = "img/booking"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        return upload_dir

    @staticmethod
    def store(bid: uuid.UUID, files, captions: List[str], db: Session):
        imgs: list[BookingImage] = []
        upload_dir = BookingImage.upload_dir()
        for idx, file in enumerate(files):
            ptf_img_id = uuid.uuid4()
            img_extension = splitext(file.filename)[1]
            ptf_img_id = str(ptf_img_id).replace("-", "")
            img_path = os.path.join(upload_dir, f"{ptf_img_id}{img_extension}")
            with open(img_path, "wb") as img_file:
                img_file.write(file.file.read())
            imgs.append(
                BookingImage(
                    id=ptf_img_id,
                    created_at=datetime.utcnow(),
                    booking_id=bid,
                    caption=captions[idx],
                    uri=f"{get_config().ROOT_PATH}/{img_path}",  # change this to not include img_extension
                )
            )
        db.add_all(imgs)


class BookingUnitBase(SQLModel):
    """
    field (quantity) int: Should always have at least 1 quantity.
    """

    work_unit_id: int = Field(foreign_key="work_units.id", primary_key=True)
    quantity: int = Field(default=1)
    description: Optional[str] = Field(nullable=True)


class BookingUnitCreate(BookingUnitBase):
    @staticmethod
    def mock(faky: Faky):
        return BookingUnitCreate(
            work_unit_id=faky.unit(),
            quantity=faky.fake.random_number(digits=2),
            description=faky.fake.word(),
        )


class BookingUnit(BookingUnitBase, table=True):
    __tablename__ = "booking_units"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, nullable=False, unique=True)
    booking_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("bookings.id", initially="DEFERRED", deferrable=True),
            primary_key=True,
        ),
    )

    @staticmethod
    def create(bid: uuid.UUID, unit: BookingUnitCreate, db: Session):
        model = BookingUnit(**unit.model_dump(), booking_id=bid)
        db.add(model)
        return model

    @staticmethod
    def create_many(bid: uuid.UUID, units: List[BookingUnitCreate], db: Session):
        models = [BookingUnit(**unit.model_dump(), booking_id=bid) for unit in units]
        db.add_all(models)
        return models


class BookingUnitView(BookingUnitBase):
    work_unit: str
    booking_id: uuid.UUID  | None = None

    @staticmethod
    def create(units, db: Session):
        work_units = WorkUnit.by_ids([unit["work_unit_id"] for unit in units], db)
        models: List[BookingUnitView] = []
        for idx, unit in enumerate(units):
            models.append(
                BookingUnitView(
                    work_unit_id=unit["work_unit_id"],
                    quantity=unit["quantity"],
                    description=unit["description"],
                    booking_id=unit["booking_unit_id"],
                    work_unit=work_units[idx][0].concat(),
                )
            )
        return models


class BookingDetailBase(SQLModel):
    title: str = Field(nullable=False)
    zipcode: str = Field(nullable=False)
    address: str = Field(nullable=False)


class BookingDetailCreate(BookingDetailBase):
    units: List[BookingUnitCreate]
    captions: List[str]

    @staticmethod
    def from_form(booking: Annotated[str, Form()]):
        try:
            json_raw = json.loads(booking)
            units = json_raw.get("units", [])
            title = json_raw.get("title", None)
            zipcode = json_raw.get("zipcode", None)
            captions = json_raw.get("captions", [])
            address = json_raw.get("address", None)
            for unit in units:
                if not unit["work_unit_id"]:
                    unit["work_unit_id"] = unit.pop("unit_id", None)
            ta = TypeAdapter(list[BookingUnitCreate])
            units = ta.validate_python(units)
            return BookingDetailCreate(
                title=title,
                zipcode=zipcode,
                units=units,
                captions=captions,
                address=address,
            )
        except Exception as e:
            raise APIError.BookingValidationException(e)

    @staticmethod
    def mock(faky: Faky, unit_count: int, caption_count: int = 0):
        unit_sample = faky.unit_sample(unit_count)
        units = [
            BookingUnitCreate(
                work_unit_id=unit,
                quantity=faky.fake.random_number(digits=2),
                description=faky.fake.word(),
            )
            for unit in unit_sample
        ]
        captions = [faky.fake.word() for _ in range(caption_count)]
        return BookingDetailCreate(
            title=faky.fake.word(),
            zipcode=faky.fake.postcode(),
            units=units,
            captions=captions,
            address=faky.fake.address(),
        )

    def to_preferences(self, cid: uuid.UUID, db):
        """Creates contractor Professions based on booking units"""
        areas = [ContractorAreaPreference(area=self.zipcode, contractor_id=cid)]
        units = [
            ContractorUnitPreference(contractor_id=cid, work_unit_id=unit.work_unit_id)
            for unit in self.units
        ]
        model = ContractorPreferencesCreate.from_units(areas=areas, units=units, db=db)
        return model


class BookingDetail(BookingDetailBase, table=True):
    __tablename__ = "bookings"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, unique=True, primary_key=True)
    homeowner_id: uuid.UUID = Field(foreign_key="homeowners.id", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    is_active: Optional[bool] = Field(default=True)
    is_booked: Optional[bool] = Field(default=False)

    @staticmethod
    def by_hid_active_list(hid: uuid.UUID, db: Session):
        return db.exec(
            select(
                BookingDetail,
                func.jsonb_agg(
                    func.jsonb_build_object(
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
                    ).distinct()
                ),
            )
            .where(
                and_(
                    BookingDetail.homeowner_id == hid,
                    BookingDetail.is_active == True,
                    BookingDetail.is_booked == False,
                )
            )
            .join(BookingUnit, BookingUnit.booking_id == BookingDetail.id)
            .join(WorkUnit, WorkUnit.id == BookingUnit.work_unit_id)
            .group_by(BookingDetail)
        ).all()

    @staticmethod
    def by_hid_active(bid: uuid.UUID, hid: uuid.UUID, db: Session):
        return db.exec(
            select(
                BookingDetail,
                func.jsonb_agg(
                    func.jsonb_build_object(
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
                    ).distinct()
                ),
                func.array_agg(
                    func.to_jsonb(Contractor.__table__.table_valued()).distinct()
                ).filter(Contractor.id.isnot(None)),
                func.jsonb_agg(
                    func.jsonb_build_object(
                        "uri",
                        BookingImage.uri,
                        "caption",
                        BookingImage.caption,
                        "created_at",
                        BookingImage.created_at,
                    ).distinct(),
                )
                .filter(
                    BookingImage.uri.isnot(None),
                )
                .label("booking_images"),
            )
            .where(
                and_(
                    BookingDetail.homeowner_id == hid,
                    BookingDetail.id == bid,
                    BookingDetail.is_active == True,
                    BookingDetail.is_booked == False,
                )
            )
            .outerjoin(
                BookingInvite,
                and_(
                    BookingInvite.booking_id == BookingDetail.id,
                    BookingInvite.accepted == True,
                    BookingInvite.rejected == False,
                ),
            )
            .outerjoin(Contractor, Contractor.id == BookingInvite.contractor_id)
            .join(BookingUnit, BookingUnit.booking_id == BookingDetail.id)
            .join(WorkUnit, WorkUnit.id == BookingUnit.work_unit_id)
            .outerjoin(BookingImage, BookingImage.booking_id == BookingDetail.id)
            .group_by(BookingDetail)
        ).first()

    @staticmethod
    def match_one(bid: uuid.UUID, cid: uuid.UUID, hid: uuid.UUID, db: Session):
        sub_query = (
            select(
                BookingDetail,
                func.array_agg(BookingUnit.work_unit_id).label("units"),
                func.count(BookingUnit.work_unit_id).label("unit_count"),
            )
            .where(
                and_(
                    BookingDetail.id == bid,
                    BookingDetail.is_booked == False,
                    BookingDetail.is_active == True,
                    BookingDetail.homeowner_id == hid,
                )
            )
            .join(BookingUnit, BookingUnit.booking_id == bid)
            .group_by(BookingDetail.id)
            .cte()
        )

        query = (
            select(
                ContractorUnitPreference.contractor_id.distinct(),
                func.count(ContractorUnitPreference.work_unit_id.distinct()),
            )
            .where(
                and_(
                    ContractorUnitPreference.contractor_id == cid,
                    ContractorUnitPreference.work_unit_id.in_(
                        select(func.unnest(sub_query.c.units))
                    ),
                ),
            )
            .join(
                ContractorAreaPreference,
                ContractorAreaPreference.area == select(sub_query.c.zipcode).scalar_subquery(),
            )
            .group_by(ContractorUnitPreference.contractor_id)
            .having(
                func.count(ContractorUnitPreference.work_unit_id.distinct())
                == select(sub_query.c.unit_count).scalar_subquery()
            )
        )
        return db.exec(query).first()

    @staticmethod
    def by_bid_with_units_is_booked(bid: uuid.UUID, db: Session):
        query = (
            select(
                BookingDetail,
                func.json_agg(
                    func.json_build_object(
                        "work_unit_id",
                        BookingUnit.work_unit_id,
                        "description",
                        BookingUnit.description,
                        "quantity",
                        BookingUnit.quantity,
                        "booking_unit_id",
                        BookingUnit.id,
                    )
                ),
            )
            .where(
                and_(
                    BookingDetail.id == bid,
                    BookingDetail.is_booked == False,
                    BookingDetail.is_active == True,
                )
            )
            .join(BookingUnit, BookingUnit.booking_id == bid)
            .group_by(BookingDetail.id)
        )

        booking = db.exec(query).first()
        return booking

    @staticmethod
    def by_hid_with_units_is_booked(hid: uuid.UUID, bid: uuid.UUID, db: Session):
        query = (
            select(
                BookingDetail,
                func.json_agg(
                    func.json_build_object(
                        "work_unit_id",
                        BookingUnit.work_unit_id,
                        "description",
                        BookingUnit.description,
                        "quantity",
                        BookingUnit.quantity,
                    )
                ),
            )
            .where(
                and_(
                    BookingDetail.id == bid,
                    BookingDetail.is_booked == False,
                    BookingDetail.is_active == True,
                    BookingDetail.homeowner_id == hid,
                )
            )
            .join(BookingUnit, BookingUnit.booking_id == bid)
            .group_by(BookingDetail.id)
        )

        booking = db.exec(query).first()
        return booking

    @staticmethod
    def by_hid_with_units_not_booked(hid: uuid.UUID, bid: uuid.UUID, db: Session):
        query = (
            select(
                BookingDetail,
                func.json_agg(
                    func.json_build_object(
                        "work_unit_id",
                        BookingUnit.work_unit_id,
                        "description",
                        BookingUnit.description,
                        "quantity",
                        BookingUnit.quantity,
                    )
                ),
            )
            .where(
                and_(
                    BookingDetail.id == bid,
                    BookingDetail.homeowner_id == hid,
                )
            )
            .join(BookingUnit, BookingUnit.booking_id == bid)
            .group_by(BookingDetail.id)
        )

        booking = db.exec(query).first()
        return booking

    @staticmethod
    def match_all(bid: uuid.UUID, db: Session):
        units_q = (
            select(
                BookingDetail.zipcode,
                func.array_agg(WorkUnit.id).label("wids"),
                func.count(WorkUnit.id).label("wid_count"),
            )
            .join(BookingDetail, BookingDetail.id == bid)
            .join(BookingUnit, BookingUnit.booking_id == BookingDetail.id)
            .where(WorkUnit.id == BookingUnit.work_unit_id)
            .group_by(BookingDetail.zipcode)
            .cte("units")
        )
        
        cnt_units_q = (
            select(
                Contractor.id,
                func.count(ContractorUnitPreference.work_unit_id.distinct()).label(
                    "matches"
                ),
            )
            .join(
                ContractorUnitPreference,
                and_(
                    ContractorUnitPreference.contractor_id == Contractor.id,
                    ContractorUnitPreference.work_unit_id.in_(
                        select(func.unnest(units_q.c.wids)).select_from(units_q)
                    ),
                ),
            )
            .group_by(Contractor)
            .cte("cnt_units")
        )
        
        cnt_area_q = (
            select(ContractorAreaPreference.contractor_id)
            .where(
                ContractorAreaPreference.contractor_id == cnt_units_q.c.id,
                ContractorAreaPreference.area == units_q.c.zipcode
            )
            .cte("cnt_areas")
        )
        
        cnt_units_filter_q = (
            select(
                cnt_units_q.c.id,
            )
            .select_from(cnt_units_q)
            .where(
                cnt_units_q.c.matches
                == select(units_q.c.wid_count).select_from(units_q).scalar_subquery()
            )
            .distinct()
            .cte("cnt_units_filter")
        )
        cnt_ids_q = (
            select(
                cnt_units_filter_q.c.id,
            )
            .join_from(
                cnt_units_filter_q,
                cnt_area_q,
                and_(
                    cnt_units_filter_q.c.id == cnt_area_q.c.contractor_id,
                ),
            )
            .distinct()
            .cte("cnt_units_ids")
        )
        query = (
            select(
                Contractor,
                func.array_agg(WorkUnit.profession.distinct()).filter(
                    WorkUnit.profession.isnot(None),
                ),
                func.array_agg(ContractorAreaPreference.area.distinct()).filter(
                    ContractorAreaPreference.area.isnot(None),
                ),
            )
            .where(Contractor.id == cnt_ids_q.c.id)
            .outerjoin(
                ContractorUnitPreference,
                ContractorUnitPreference.contractor_id == Contractor.id,
            )
            .outerjoin(WorkUnit, WorkUnit.id == ContractorUnitPreference.work_unit_id)
            .outerjoin(
                ContractorAreaPreference,
                ContractorAreaPreference.contractor_id == Contractor.id,
            )
            .distinct()
            .group_by(Contractor)
        )

        contractors = db.execute(query).all()

        return contractors

    @staticmethod
    def match_all_by_hid_and_cid(hid: uuid.UUID, cid: uuid.UUID, db: Session):
        units_q = (
            select(ContractorUnitPreference.work_unit_id)
            .where(ContractorUnitPreference.contractor_id == cid)
            .cte("cnt_units")
        )
        booking_units_q = (
            select(
                BookingDetail.id,
                func.count(BookingUnit.work_unit_id).label("wid_count"),
            )
            .where(
                and_(
                    BookingDetail.homeowner_id == hid,
                    BookingDetail.is_active == True,
                    BookingDetail.is_booked == False,
                )
            )
            .join(BookingUnit, BookingUnit.booking_id == BookingDetail.id)
            .group_by(BookingDetail)
            .distinct()
            .cte("b_units")
        )
        query = (
            select(
                BookingDetail,
                func.jsonb_agg(
                    func.jsonb_build_object(
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
                    ).distinct()
                ),
            )
            .join(
                BookingUnit,
                BookingUnit.work_unit_id.in_(select(units_q.c.work_unit_id)),
            )
            .join(WorkUnit, WorkUnit.id == BookingUnit.work_unit_id)
            .where(
                and_(
                    BookingDetail.homeowner_id == hid,
                    BookingDetail.id == BookingUnit.booking_id,
                )
            )
            .having(
                func.count(BookingUnit.work_unit_id)
                >= select(booking_units_q.c.wid_count)
                .select_from(booking_units_q)
                .where(booking_units_q.c.id == BookingDetail.id)
                .scalar_subquery()
            )
            .group_by(BookingDetail)
            .distinct()
        )
        return db.exec(query).all()

    @staticmethod
    def create(hid: uuid.UUID, booking: BookingDetailCreate, db: Session):
        model = BookingDetail(
            homeowner_id=hid,
            title=booking.title,
            zipcode=booking.zipcode,
            address=booking.address,
        )
        db.add(model)
        return model


class BookingDetailViewBase(SQLModel):
    id: uuid.UUID
    title: str
    zipcode: str
    units: List[BookingUnitView]
    images: List[ImageView] | None = None

    # quote: QuoteView


class HomeownerBookingDetailView(BookingDetailViewBase):
    """
    Homeowner booking card as seen by the homeowner
    Only available after creating a bookinh thru the quiz

    field (accepted_contractors)
    - Only avaiable after homeowner send an invite
    and contractor accepts it
    """

    address: str
    accepted_contractors: List[ContractorPublicView] | None = None


class ContractorBookingDetailView(BookingDetailViewBase):
    """
    Contractor booking card as seen by the contractor

    Note: Only avaiable after homeowner send an invite
    and contractor accepts it
    """

    homeowner: HomeownerPublicView

class BookingInviteCreate(SQLModel):
    booking_id: uuid.UUID
    contractor_id: uuid.UUID


class BookingInvite(SQLModel, table=True):
    __tablename__ = "booking_invites"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, nullable=False, unique=True)
    booking_id: uuid.UUID = Field(foreign_key="bookings.id", primary_key=True)
    contractor_id: uuid.UUID = Field(foreign_key="contractors.id", primary_key=True)
    accepted: Optional[bool] = Field(default=False)
    rejected: Optional[bool] = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    @staticmethod
    def match(cid: uuid.UUID, bid: uuid.UUID, db: Session):
        query = (
            select(BookingInvite)
            .where(
                and_(
                    # for better client-side errors, check for this in the rotue
                    # BookingInvite.accepted == False,
                    # BookingInvite.rejected == False,
                    BookingInvite.contractor_id == cid,
                    BookingInvite.booking_id == bid,
                )
            )
            .join(
                BookingDetail,
                and_(
                    BookingDetail.id == BookingInvite.booking_id,
                    BookingDetail.is_active == True,
                    BookingDetail.is_booked == False,
                ),
            )
        )
        model = db.execute(query).first()
        return model

    @staticmethod
    def by_cid(cid: uuid.UUID, bid: uuid.UUID, db: Session):
        """Caller MUST check that bid is valid"""
        query = select(BookingInvite).where(
            and_(
                # for better client-side errors, check for this in the rotue
                BookingInvite.accepted == True,
                BookingInvite.rejected == False,
                BookingInvite.contractor_id == cid,
                BookingInvite.booking_id == bid,
            )
        )
        model = db.execute(query).first()
        return model

    @staticmethod
    def by_cid_unchecked(cid: uuid.UUID, bid: uuid.UUID, db: Session):
        """Caller MUST check that bid is valid"""
        query = select(BookingInvite).where(
            and_(
                # for better client-side errors, check for this in the rotue
                BookingInvite.contractor_id == cid,
                BookingInvite.booking_id == bid,
            )
        )
        model = db.execute(query).first()
        return model

    @staticmethod
    def cids_by_bid(bid: uuid.UUID, db: Session):
        """Caller MUST check that bid is valid"""
        query = select(BookingInvite.contractor_id).where(
            and_(
                # for better client-side errors, check for this in the rotue
                BookingInvite.accepted == True,
                BookingInvite.rejected == False,
                BookingInvite.booking_id == bid,
            )
        )
        model = db.execute(query).all()
        return model

    @staticmethod
    def accepted_by_cid(cid: uuid.UUID, db: Session):
        query = (
            select(
                BookingInvite.booking_id,
                BookingDetail.title,
                BookingDetail.created_at,
                Homeowner.avatar_uri,
                Homeowner.first_name,
                Homeowner.last_name,
                func.jsonb_agg(
                    func.jsonb_build_object(
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
                    ).distinct()
                ),
            )
            .where(
                and_(
                    BookingInvite.rejected == False,
                    BookingInvite.accepted == True,
                    BookingInvite.contractor_id == cid,
                )
            )
            .join(
                BookingDetail,
                and_(
                    BookingDetail.id == BookingInvite.booking_id,
                    BookingDetail.is_active == True,
                    BookingDetail.is_booked == False,
                ),
            )
            .join(BookingUnit, BookingUnit.booking_id == BookingDetail.id)
            .join(WorkUnit, WorkUnit.id == BookingUnit.work_unit_id)
            .join(Homeowner, Homeowner.id == BookingDetail.homeowner_id)
            .group_by(BookingInvite, BookingDetail, Homeowner)
        )
        models = db.execute(query).all()
        return models

    @staticmethod
    def invites_ids_by_cid(cid: uuid.UUID, db: Session):
        query = (
            select(
                BookingInvite.booking_id,
                BookingDetail.title,
                BookingDetail.created_at,
                Homeowner.avatar_uri,
                Homeowner.first_name,
                Homeowner.last_name,
                func.jsonb_agg(
                    func.jsonb_build_object(
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
                    ).distinct()
                ),
            )
            .where(
                and_(
                    BookingInvite.rejected == False,
                    BookingInvite.accepted == False,
                    BookingInvite.contractor_id == cid,
                )
            )
            .join(
                BookingDetail,
                and_(
                    BookingDetail.id == BookingInvite.booking_id,
                    BookingDetail.is_active == True,
                    BookingDetail.is_booked == False,
                ),
            )
            .join(Homeowner, Homeowner.id == BookingDetail.homeowner_id)
            .join(BookingUnit, BookingUnit.booking_id == BookingDetail.id)
            .join(WorkUnit, WorkUnit.id == BookingUnit.work_unit_id)
            .group_by(BookingInvite, BookingDetail, Homeowner)
        )
        models = db.execute(query).all()
        return models

    @staticmethod
    def create(booking: BookingInviteCreate, db: Session):
        model = booking.model_dump()
        model = BookingInvite(**model)
        db.add(model)
        return model

    @staticmethod
    def create_accepted(booking: BookingInviteCreate, db: Session):
        model = booking.model_dump()
        model = BookingInvite(**model)
        model.accepted = True
        model.rejected = False
        db.add(model)
        return model

    @staticmethod
    def create_rejected(booking: BookingInviteCreate, db: Session):
        model = booking.model_dump()
        model = BookingInvite(**model)
        model.accepted = False
        model.rejected = True
        db.add(model)
        return model


class ContractorBookingInviteView(SQLModel):
    """
    field (created_at): when homeowner initiated the invite
    """

    created_at: datetime
    accepted: bool = False
    rejected: bool = False


class HomeownerBookingItem(SQLModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    booking_units: List[BookingUnitView]


class ContractorBookingItem(HomeownerBookingItem):
    avatar_uri: str
    first_name: str
    last_name: str
    booking_units: List[BookingUnitView]


class HomeownerBookingList(SQLModel):
    bookings: List[HomeownerBookingItem]


class ContractorBookingList(SQLModel):
    bookings: List[ContractorBookingItem]
