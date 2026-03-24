source "$(dirname "$0")/locust_config.sh"
PROJECT_ROOT="$(dirname "$0")/.."
set -a
source "$PROJECT_ROOT/.env"
set +a

echo "check number of orders placed by locust users..."
docker exec -it flash_sale_postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "SELECT COUNT(*) FROM orders WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'locust_%');"

echo "check remaining stock for the target product..."
docker exec -it flash_sale_postgres psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "SELECT stock FROM products WHERE id = $TARGET_PRODUCT_ID;"

echo "check remaining stock in Redis for the target product..."
docker exec -it flash_sale_redis redis-cli -a $REDIS_PASSWORD \
  GET stock:product:$TARGET_PRODUCT_ID
