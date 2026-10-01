FROM python:3.12-slim
WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PORT=8080
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY packs ./packs
CMD exec uvicorn kavach.main:app --host 0.0.0.0 --port ${PORT}
