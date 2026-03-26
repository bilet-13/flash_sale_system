# Flash Sale System

![CI](https://github.com/bilet-13/flash_sale_system/actions/workflows/deploy.yml/badge.svg)

A high-concurrency flash sale API built to handle simultaneous purchase requests without overselling.

## Tech Stack

- **FastAPI** — REST API
- **PostgreSQL** — order and user storage
- **Redis** — atomic inventory deduction via Lua Script
- **RabbitMQ** — async order processing
- **Nginx** — reverse proxy
- **Docker Compose** — container orchestration
- **AWS EC2** — deployment

## Architecture

```
Client → Nginx → FastAPI → Redis Lua Script (atomic deduction)
                               ↓
                          RabbitMQ → Worker → PostgreSQL
```

## Key Results

| Mode              | RPS | Median Latency | Failure Rate |
| ----------------- | --- | -------------- | ------------ |
| Direct PostgreSQL | 72  | 27ms           | 0%           |
| Redis + async     | 144 | 19ms           | 0%           |

Under 300 concurrent users, direct DB mode produced **6,110 oversold orders** due to race conditions. Redis Lua Script reduced this to **zero**.

## API Endpoints

| Method | Endpoint                       | Description          |
| ------ | ------------------------------ | -------------------- |
| POST   | `/auth/register`               | Register user        |
| POST   | `/auth/login`                  | Login, get JWT token |
| GET    | `/products`                    | List products        |
| POST   | `/flash-sale/buy/{product_id}` | Purchase item        |
| GET    | `/orders`                      | Get my orders        |
| GET    | `/health`                      | Health check         |

## Run Locally

```bash
git clone https://github.com/bilet-13/flash_sale_system.git
cd flash_sale_system
cp .env_example .env
docker-compose up -d
```

API docs available at `http://localhost/docs`

## Load Testing

```bash
bash locust_test/locust.sh
```

Locust UI at `http://localhost:8089`
