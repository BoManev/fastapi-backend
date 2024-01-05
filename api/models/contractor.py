import os
from posixpath import splitext
import uuid
from fastapi import Form
from pydantic import BaseModel, EmailStr, SecretStr
import requests
from sqlalchemy import UUID, ForeignKey, func
from sqlmodel import SQLModel, Field, Column, Session, select
from typing import Annotated, List, Optional
from api.config import get_config
from api.models.quiz.model import WorkUnit
from api.models.user import User, UserCreate, UserRole
from api.models.utils import RatingBase
from api.utils.faky import Faky


class ContractorAnalytics(SQLModel, table=True):
    __tablename__ = "contractor_analytics"
    tasks: int = Field(default=0)
    completed_projects: int = Field(default=0)
    reviews: int = Field(default=0)
    contractor_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("contractors.id", initially="DEFERRED", deferrable=True),
            primary_key=True,
        )
    )

    @staticmethod
    def by_cid(cid: uuid.UUID, db: Session):
        return db.exec(
            select(ContractorAnalytics).where(ContractorAnalytics.contractor_id == cid)
        ).first()


class ContractorRating(RatingBase):
    pass


class ContractorAreaPreference(SQLModel, table=True):
    __tablename__ = "contractor_area_preferences"

    area: str = Field(primary_key=True)
    contractor_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("contractors.id", initially="DEFERRED", deferrable=True),
            primary_key=True,
        )
    )

    @staticmethod
    def by_cid(cid: uuid.UUID, db: Session):
        query = select(ContractorAreaPreference).where(
            ContractorAreaPreference.contractor_id == cid
        )
        preferences = db.exec(query).all()
        return preferences

    @staticmethod
    def create(cid: uuid.UUID, areas: List[str], db: Session):
        models: List[ContractorAreaPreference] = []
        for area in areas:
            models.append(ContractorAreaPreference(contractor_id=cid, area=area))
        db.add_all(models)
        return models

    @staticmethod
    def clear(cid: uuid.UUID, db: Session):
        areas = ContractorAreaPreference.by_cid(cid, db)
        if areas:
            for area in areas:
                db.delete(area)

    @staticmethod
    def mock(faky: Faky, cid: uuid.UUID):
        return ContractorAreaPreference(contractor_id=cid, area=faky.fake.postcode())

    @staticmethod
    def mocks(faky: Faky, cid: uuid.UUID, count: int):
        areas = set()
        while len(areas) < count:
            postcode = faky.fake.postcode()
            areas.add(postcode)
        models: List[ContractorAreaPreference] = []
        for area in areas:
            models.append(ContractorAreaPreference(contractor_id=cid, area=area))
        return models


class ContractorUnitPreference(SQLModel, table=True):
    __tablename__ = "contractor_profession_preferences"

    work_unit_id: int = Field(foreign_key="work_units.id", primary_key=True)
    contractor_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("contractors.id", initially="DEFERRED", deferrable=True),
            primary_key=True,
        )
    )

    @staticmethod
    def by_cid(cid: uuid.UUID, db: Session):
        query = select(ContractorUnitPreference).where(
            ContractorUnitPreference.contractor_id == cid
        )
        preferences = db.exec(query).all()
        return preferences

    @staticmethod
    def create_from_ids(cid: uuid.UUID, work_unit_ids: List[int], db: Session):
        models: List[ContractorUnitPreference] = []
        for unit in work_unit_ids:
            models.append(ContractorUnitPreference(contractor_id=cid, work_unit_id=unit))

        db.add_all(models)
        return models

    @staticmethod
    def create_from_professions(cid: uuid.UUID, professions: List[str], db: Session):
        unit_ids = WorkUnit.professions_to_ids(professions, db)
        models: List[ContractorUnitPreference] = []
        for unit in unit_ids:
            models.append(ContractorUnitPreference(contractor_id=cid, work_unit_id=unit[0]))
        db.add_all(models)
        return models

    @staticmethod
    def clear(cid: uuid.UUID, db: Session):
        units = ContractorUnitPreference.by_cid(cid, db)
        if units:
            for unit in units:
                db.delete(unit)

    @staticmethod
    def mock(faky: Faky, cid: uuid.UUID):
        return ContractorUnitPreference(contractor_id=cid, profession_id=faky.unit())

    @staticmethod
    def mocks(faky: Faky, cid: uuid.UUID, count: int):
        units = faky.unit_sample(count)
        models: List[ContractorUnitPreference] = []
        for unit in units:
            models.append(ContractorUnitPreference(contractor_id=cid, work_unit_id=unit))
        return models


class ContractorPreferencesCreate(BaseModel):
    areas: Optional[List[str]]
    professions: Optional[List[str]]

    @staticmethod
    def from_professions(
        areas: List[ContractorAreaPreference],
        professions: List[str],
    ):
        return ContractorPreferencesCreate(
            areas=[area.area for area in areas],
            professions=professions,
        )

    @staticmethod
    def from_units(
        areas: List[ContractorAreaPreference],
        units: List[ContractorUnitPreference],
        db: Session,
    ):
        return ContractorPreferencesCreate(
            areas=[area.area for area in areas],
            professions=[
                unit[0]
                for unit in WorkUnit.ids_to_professions([unit.work_unit_id for unit in units], db)
            ],
        )


class ContractorPreferencesView(BaseModel):
    """
    Contractors can only select work preferences by profession.
    """

    areas: Optional[List[str]]
    professions: Optional[list[str]]

    @staticmethod
    def create(
        areas: List[ContractorAreaPreference],
        units: List[ContractorUnitPreference],
        db: Session,
    ):
        return ContractorPreferencesView(
            areas=[area.area for area in areas],
            professions=[
                unit[0]
                for unit in WorkUnit.ids_to_professions([unit.work_unit_id for unit in units], db)
            ],
        )


class ContractorCreate(UserCreate):
    first_name: str
    last_name: str
    bio: Optional[str] = None

    @staticmethod
    def from_form(
        first_name: Annotated[str, Form()],
        last_name: Annotated[str, Form()],
        phone_number: Annotated[str, Form()],
        password: Annotated[SecretStr, Form()],
        email: Annotated[EmailStr, Form()],
        bio: Annotated[str, Form()] = None,
    ):
        return ContractorCreate(
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            password=password,
            email=email,
            bio=bio,
        )

    @staticmethod
    def mock(faky: Faky, password: str):
        return ContractorCreate(
            first_name=faky.fake.first_name(),
            last_name=faky.fake.last_name(),
            email=faky.fake.email(),
            phone_number=faky.fake.phone_number(),
            password=SecretStr(password),
            bio="bio",
        )


class Contractor(ContractorRating, table=True):
    __tablename__ = "contractors"
    id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("users.id", initially="DEFERRED", deferrable=True),
            primary_key=True,
        )
    )
    first_name: str = Field(nullable=False)
    last_name: str = Field(nullable=False)
    bio: Optional[str] = Field(nullable=True, default=None)
    avatar_uri: Optional[str] = Field(nullable=True, default=None)

    @staticmethod
    def by_cid(cid: uuid.UUID, db: Session):
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
            .where(Contractor.id == cid)
            .outerjoin(
                ContractorUnitPreference,
                ContractorUnitPreference.contractor_id == Contractor.id,
            )
            .outerjoin(WorkUnit, WorkUnit.id == ContractorUnitPreference.work_unit_id)
            .outerjoin(
                ContractorAreaPreference,
                ContractorAreaPreference.contractor_id == Contractor.id,
            )
            .group_by(Contractor)
        )
        contractor = db.exec(query).first()
        return contractor

    @staticmethod
    def by_cids(cids: List[uuid.UUID], db: Session):
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
            .where(Contractor.id.in_(cids))
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
        contractor = db.exec(query).all()
        return contractor

    @staticmethod
    def by_email(email: str, db: Session):
        query = select(Contractor).join(User, User.id == Contractor.id).where(User.email == email)
        contractor = db.exec(query).first()
        return contractor

    @staticmethod
    def create(contractor: ContractorCreate, db: Session, avatar=None):
        id = uuid.uuid4()
        user = User(
            id=id,
            phone_number=contractor.phone_number,
            email=contractor.email,
            password=contractor.password.get_secret_value(),
            role=UserRole.Contractor,
        )
        upload_folder = "img/contractor/"
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        if avatar:
            img_extension = splitext(avatar.filename)[1]
            avatar_img_id = str(id).replace("-", "")
            img_path = os.path.join(upload_folder, f"{avatar_img_id}{img_extension}")
            with open(img_path, "wb") as img_file:
                img_file.write(avatar.file.read())
            avatar_uri=f"{get_config().ROOT_PATH}/{img_path}"
        else:
            try:
                external_api_url = f"https://ui-avatars.com/api/?background=7D8790&color=ffffff&name={contractor.first_name[0]}+{contractor.last_name[0]}"
                response = requests.get(external_api_url)
                response.raise_for_status()
                img_extension = ".png"
                avatar_img_id = str(id).replace("-", "")
                img_path = os.path.join(upload_folder, f"{avatar_img_id}{img_extension}")
                with open(img_path, "wb") as img_file:
                    img_file.write(response.content)
                avatar_uri=f"{get_config().ROOT_PATH}/{img_path}"
            except:
                avatar_uri=None

        db.add(user)
        cnt = Contractor(
            id=id,
            first_name=contractor.first_name,
            last_name=contractor.last_name,
            bio=contractor.bio,
            avatar_uri=avatar_uri,
        )
        db.add(cnt)
        db.add(ContractorAnalytics(contractor_id=cnt.id))
        return cnt, user


class ContractorPublicView(ContractorRating):
    id: uuid.UUID
    first_name: str
    last_name: str
    avatar_uri: str | None = None
    bio: Optional[str]
    professions: List[str] | None = None
    areas: List[str] | None = None

    @staticmethod
    def create(contractor: Contractor, professions: List[str] = None, areas: List[str] = None):
        return ContractorPublicView(**contractor.model_dump(), professions=professions, areas=areas)

    @staticmethod
    def create_many(contractors: List[Contractor]):
        return [ContractorPublicView(**contractor.model_dump()) for contractor in contractors]


class ContractorPrivateView(ContractorRating):
    id: uuid.UUID
    first_name: str
    last_name: str
    avatar_uri: str | None = None
    email: EmailStr
    phone_number: str
    bio: Optional[str]
    professions: List[str] | None = None
    areas: List[str] | None = None


class SearchContractorList(SQLModel):
    contractors: List[ContractorPublicView]
