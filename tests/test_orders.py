from app.models import Product


def create_test_product(db, stock=10):
    product = Product(name="Order Test Item", price=50.0, stock=stock)
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


def test_order_after_purchase(client, db):
    product = create_test_product(db, stock=10)
    headers = register_and_login(client)

    # 下單
    buy_response = client.post(
        f"/flash-sale/buy/{product.id}",
        json={"quantity": 2},
        headers=headers
    )
    assert buy_response.status_code == 200
    order_id = buy_response.json()["order_id"]

    # 查訂單詳情
    response = client.get(f"/orders/{order_id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["quantity"] == 2
    assert body["product"]["id"] == product.id
