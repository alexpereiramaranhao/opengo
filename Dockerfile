FROM python:3.12-slim
LABEL authors="Alex Pereira Maranhão"

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root

COPY opengo-jobs /app/opengo-jobs/

CMD ["python", "opengo-jobs/og_retrieve_apis_job.py"]