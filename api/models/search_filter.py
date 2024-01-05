from typing import List, Optional
from sqlalchemy import and_, func
from sqlmodel import SQLModel, Session, select

from api.models.contractor import (
    Contractor,
    ContractorAreaPreference,
    ContractorUnitPreference,
)
from api.models.quiz.model import WorkUnit


class Filter(SQLModel):
    professions: List[str]
    zipcode: int

    @staticmethod
    def from_form():
        pass

    @staticmethod
    def by_units_and_area(professions: List[str], area: str, db: Session):
        units_q = (
            select(
                func.array_agg(WorkUnit.id).label("wids"),
                func.count(WorkUnit.id).label("wid_count"),
            )
            .where(WorkUnit.profession.in_(professions))
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
                ContractorAreaPreference.area == area,
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
        return db.exec(query).all()
