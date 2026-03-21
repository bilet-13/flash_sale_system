from app.models import Product


def create_test_product(db, name="Test Product", price=100.0, stock=50):
    product = Product(name=name, price=price, stock=stock)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def test_get_all_products(client, db):
    create_test_product(db, name="Product A")
    create_test_product(db, name="Product B")
    create_test_product(db, name="Product C")

    response = client.get("/products")

    assert response.status_code == 200
    assert len(response.json()) == 3


def test_get_product_by_id(client, db):
    product = create_test_product(
        db, name="Flash Speaker", price=299.0, stock=10)

    response = client.get(f"/products/{product.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Flash Speaker"
    assert float(body["price"]) == 299.0
    assert body["stock"] == 10


def test_get_product_not_found(client):
    response = client.get("/products/99999")

    assert response.status_code == 404


def test_get_product_stock(client, db):
    product = create_test_product(db, stock=42)

    response = client.get(f"/products/{product.id}/stock")

    assert response.status_code == 200
    assert response.json()["stock"] == 42
