FROM python:3.12-slim
LABEL authors="Alex Pereira Maranhão"

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root

COPY / /app/opengo/

CMD ["python", "/app/opengo/pengo_analytics/og_analytics.py"]
