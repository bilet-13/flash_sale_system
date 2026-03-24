source "$(dirname "$0")/locust_config.sh"

echo "check number  of orders placed by locust users..."
docker exec -it flash_sale_postgres psql -U flash_user -d flash_sale_db \
  -c "SELECT COUNT(*) FROM orders WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'locust_%');"


echo "check remaining stock for the target product..."
docker exec -it flash_sale_postgres psql -U flash_user -d flash_sale_db \
  -c "SELECT stock FROM products WHERE id = $TARGET_PRODUCT_ID;"

echo "check remaining stock in Redis for the target product..."
docker exec -it flash_sale_redis redis-cli -a redis_secure_pass_2024 \
  GET stock:product:$TARGET_PRODUCT_ID
