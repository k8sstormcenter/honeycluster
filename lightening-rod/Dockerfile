# syntax=docker/dockerfile:1

FROM cgr.dev/chainguard/python:latest-dev as dev

WORKDIR /app
RUN python -m venv venv
ENV PATH="/app/venv/bin":$PATH

COPY . .
RUN pip install poetry 
RUN poetry install --no-root


EXPOSE 8000
ENV PATH="/app/venv/bin:$PATH"

ENTRYPOINT ["poetry" , "run", "python", "manual.py"]
