source "$(dirname "$0")/locust_config.sh"
PROJECT_ROOT="$(dirname "$0")/.."
set -a
source "$PROJECT_ROOT/.env"
set +a

# clean data
docker exec -it flash_sale_postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "DELETE FROM orders WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'locust_%');"
docker exec -it flash_sale_postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "DELETE FROM users WHERE username LIKE 'locust_%';"

# set stock in both Postgres and Redis
docker exec -it flash_sale_postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "UPDATE products SET stock = $INITIAL_STOCK WHERE id = $TARGET_PRODUCT_ID;"
docker exec -it flash_sale_redis redis-cli -a $REDIS_PASSWORD \
  SET stock:product:$TARGET_PRODUCT_ID $INITIAL_STOCK

export TARGET_PRODUCT_ID
cd "$(dirname "$0")/.." && .venv/bin/locust -f locust/locustfile.py --host=http://localhost:8000
