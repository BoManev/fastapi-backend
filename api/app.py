import os
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
import api.models as models  # noqa: F401
from api.config import get_config
from api.route import api
from api.core.db import get_db


def custom_generate_unique_id(route: APIRoute):
    return f"{list(route.methods)[0]}{route.tags[0]}-{route.name}"


# from fastapi_events.middleware import EventHandlerASGIMiddleware
# from fastapi_events.handlers.local import local_handler
# app.add_middleware(EventHandlerASGIMiddleware, handlers=[local_handler])

initialized = False

def start():
    config = get_config()
    app = FastAPI(
        title=config.PROJECT_NAME,
        version=config.VERSION,
        description=config.DESCRIPTION,
        docs_url=f"{config.ROOT_PATH}/docs",
        openapi_url=f"{config.ROOT_PATH}/openapi.json",
        generate_unique_id_function=custom_generate_unique_id,
    )

    @app.on_event("startup")
    def startup():
        db = get_db()
        db.init_db()

        if config.ENV != "prod":
            import shutil

            shutil.rmtree("img/", ignore_errors=True)

        upload_dir = "img"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        app.mount(f"{config.ROOT_PATH}/img", StaticFiles(directory="img"), name="static")


    app.include_router(api)
    return app
