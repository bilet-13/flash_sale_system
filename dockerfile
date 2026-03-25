
FROM python:3.13-slim-bookworm
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./requirements.txt ./
RUN pip install -r requirements.txt

COPY ./worker.py ./
COPY ./app ./app


EXPOSE 8000