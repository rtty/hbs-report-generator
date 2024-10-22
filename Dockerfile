FROM python:3.11-slim

WORKDIR /app
RUN pip install poetry
COPY poetry.lock pyproject.toml /app/

RUN poetry config virtualenvs.create false
RUN poetry install

COPY . .
RUN ["chmod", "+x", "/app/generator-local.sh"]

CMD ["bash", "/app/generator-local.sh"]
