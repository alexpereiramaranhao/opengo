FROM python:3.12-slim
LABEL authors="Alex Pereira Maranhão"

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root

COPY / /app/opengo/

HEALTHCHECK CMD ["curl", "--fail", "http://localhost:5000/_stcore/health"]

ENTRYPOINT ["streamlit", "run", "/app/opengo/opengo_analytics/og_analytics.py", "--server.port=5000", "--server.address=0.0.0.0"]