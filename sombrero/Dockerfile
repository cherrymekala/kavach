# Build context is the repo root (see cloudbuild.yaml) so packs come straight from magellan/.
FROM python:3.12-slim
WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PORT=8080
COPY sombrero/pyproject.toml ./
COPY sombrero/src ./src
RUN pip install --no-cache-dir .
COPY magellan/packs ./packs
CMD exec uvicorn kavach.main:app --host 0.0.0.0 --port ${PORT}
