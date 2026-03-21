from app.models import Product

# ── Helpers ─────────────────────────────────────


def create_test_product(db, stock=10):
    product = Product(name="Flash Item", price=99.0, stock=stock)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def register_and_login(client):
    client.post("/auth/register", json={
        "username": "buyer",
        "email": "buyer@example.com",
        "password": "buyerpass"
    })
    response = client.post("/auth/login", data={
        "username": "buyer",
        "password": "buyerpass"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Flash Sale 測試 ──────────────────────────────

def test_buy_success(client, db):
    product = create_test_product(db, stock=10)
    headers = register_and_login(client)

    response = client.post(
        f"/flash-sale/buy/{product.id}", json={"quantity": 1}, headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_buy_reduces_stock(client, db):
    product = create_test_product(db, stock=10)
    headers = register_and_login(client)

    client.post(f"/flash-sale/buy/{product.id}",
                json={"quantity": 3}, headers=headers)

    # 從 Redis 查庫存
    response = client.get(f"/products/{product.id}/stock")
    assert response.json()["stock"] == 7


def test_buy_exceeds_stock(client, db):
    product = create_test_product(db, stock=5)
    headers = register_and_login(client)

    response = client.post(
        f"/flash-sale/buy/{product.id}", json={"quantity": 10}, headers=headers)

    assert response.status_code == 422


def test_buy_product_not_found(client, db):
    headers = register_and_login(client)

    response = client.post("/flash-sale/buy/99999",
                           json={"quantity": 1}, headers=headers)

    assert response.status_code == 404


def test_buy_without_login(client, db):
    product = create_test_product(db, stock=10)

    response = client.post(
        f"/flash-sale/buy/{product.id}", json={"quantity": 1})

    assert response.status_code == 401
