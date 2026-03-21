
# ── 共用的測試資料 ──────────────────────────────
TEST_USER = {
    "username": "testuser",
    "email": "testuser@example.com",
    "password": "testpassword"
}


def register_user(client):
    """helper：註冊一個測試用戶，避免每個測試都重複寫這段"""
    return client.post("/auth/register", json=TEST_USER)


# ── Register 測試 ───────────────────────────────
def test_register_success(client):

    response = register_user(client)
    assert response.status_code == 201


def test_repeat_register(client):

    response = client.post("/auth/register", json={
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpassword"
    })

    assert response.status_code == 201

    response = client.post("/auth/register", json={
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpassword"
    })

    assert response.status_code == 400


def test_register_duplicate_email(client):
    # 第一次註冊
    register_user(client)

    # 同樣 email，不同 username → 應該失敗
    response = client.post("/auth/register", json={
        "username": "otheruser",
        "email": TEST_USER["email"],  # 同樣的 email
        "password": "testpassword"
    })

    assert response.status_code == 400


# ── Login 測試 ──────────────────────────────────
def test_login_success(client):
    register_user(client)

    response = client.post("/auth/login", data={
        "username": TEST_USER["username"],
        "password": TEST_USER["password"]
    })

    assert response.status_code == 200

    body = response.json()
    assert "access_token" in body        # token 存在
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client):
    register_user(client)

    response = client.post("/auth/login", data={
        "username": TEST_USER["username"],
        "password": "wrongpassword"
    })

    assert response.status_code == 401


def test_login_not_registered(client):
    # 不先註冊，直接登入
    response = client.post("/auth/login", data={
        "username": "nobody",
        "password": "testpassword"
    })

    assert response.status_code == 401
