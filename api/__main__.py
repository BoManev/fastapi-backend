import os
import uvicorn
from api.config import get_config
import threading
import time
from api.utils.mock_generator import generate_mocks
from alembic.config import Config
from alembic import command
from api.core.db import DB

def mock_thread():
    print("[mocks] starting...")
    # wait for server to start
    time.sleep(6)
    generate_mocks()
    print("[mocks] done")
    
config = get_config()

if config.ENV == 'prod':
    print("[migrations] starting...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("[migrations] done")
    print('[work units] initializing...')
    DB().init_work_units()
    print('[work units] done')

if config.MOCK_DB:
    mocker = threading.Thread(target=mock_thread)
    mocker.start()

if config.ENV == "prod":
    uvicorn.run(
        "api.app:start",
        host="0.0.0.0",
        port=80,
        factory=True,
        workers=2
    )
else:
    uvicorn.run(
        "api.app:start",
        host="0.0.0.0",
        port=80,
        reload=True,
        factory=True,
    )


# 2.58 with 2 workers
