from functools import lru_cache
from pydantic import PostgresDsn
from typing import Annotated, Any
from fastapi import Depends
from sqlalchemy.ext.declarative import declarative_base
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.engine import Engine
from api.config import get_config
from api.models.quiz.utils import create_work_units


class DB:
    engine: Engine
    
    def __init__(self):
        config = get_config()
        db_url = PostgresDsn(
            f"postgresql://{config.POSTGRES_USER}:{config.POSTGRES_PASSWORD}@{config.POSTGRES_HOST}:5432/{config.POSTGRES_DB}"
        )
        self.engine = (
            create_engine(
                db_url.unicode_string(),
                echo=True,
            )
            if config.DEBUG
            else create_engine(
                db_url.unicode_string(),
            )
        )
    def create_base(self):
        import api.models as models  # noqa: F401
        base = declarative_base()
        for model_name in dir(models):
            model = getattr(models, model_name)
            if isinstance(model, type) and issubclass(model, SQLModel):
                setattr(base, model_name, model)
        return base

    def init_db(self, force: bool = False):
        import api.models as models  # noqa: F401

        if get_config().ENV == "dev" or force:
            SQLModel.metadata.drop_all(self.engine)
            SQLModel.metadata.create_all(self.engine)
            models.WorkUnit.init_table(self.engine)
            self.init_work_units()

    def init_work_units(self):
        with Session(self.engine) as db:
            create_work_units(db)

@lru_cache()
def get_db():
    return DB()


def get_session_db():
    with Session(get_db().engine, autoflush=False) as session:
        yield session


SessionDB = Annotated[Session, Depends(get_session_db)]
