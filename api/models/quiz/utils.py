from sqlmodel import Session
from api.models.quiz.model import (
    WorkUnit,
    WorkUnitCreate,
    WorkUnits,
)


def create_work_units(db: Session):
    raw_units = WorkUnits
    for line in raw_units:
        units = WorkUnitCreate.from_line(line)
        for unit in units:
            work_unit = WorkUnit(
                area=unit.area,
                location=unit.location,
                category=unit.category,
                subcategory=unit.subcategory,
                action=unit.action,
                quantity=unit.quantity,
                profession=unit.profession,
            )
            db.add(work_unit)
        db.commit()
    # view = models.WorkUnitView.to_json(db)
