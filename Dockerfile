# ENV
ARG APPNAME="sitesync"

# STAGE 1: deps
FROM python:3.11 as deps
WORKDIR /tmp
RUN pip install poetry
COPY ./pyproject.toml ./poetry.lock* /tmp/
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --dev

# STAGE 2: app
FROM python:3.11 as backend
COPY --from=deps /tmp/requirements.txt .
RUN apt-get update && apt-get install --assume-yes --no-install-recommends
ARG APPNAME
RUN adduser --system --group --home /home/${APPNAME} ${APPNAME}
USER ${APPNAME}
RUN python -m pip install --upgrade pip --no-cache-dir && \
    python -m pip install --requirement "requirements.txt" --no-cache-dir
# remove in prod
ENV PYTHONBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /home/${APPNAME}
# add in prod
# COPY ./api api
# COPY ./test test
COPY ./alembic.ini .
COPY ./alembic alembic/
COPY .env .
ENV PYTHONPATH=/home/${APPNAME}