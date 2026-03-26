"""
***
Do not use locust to run the file directly,
Use locust.sh instead, which will set the target product id and initial stock before running locust.
***
"""

from locust import HttpUser, task, between
import os
import random

TARGET_PRODUCT_ID = int(os.environ.get("TARGET_PRODUCT_ID", 1))

# 壓測目標商品（確保這個商品在 DB 存在，且 Redis 庫存夠大）
TARGET_PRODUCT_ID = 999

# 預建用戶數量（對應 setup 腳本建立的數量）
PRE_CREATED_USERS = 300


class RealisticUser(HttpUser):
    """
    模擬真實用戶行為：先瀏覽商品，再搶購，偶爾查訂單
    wait_time 模擬用戶思考/操作的間隔
    """
    wait_time = between(0.5, 1.5)

    def on_start(self):
        """
        每個虛擬用戶「誕生」時執行一次。
        從預建用戶中隨機挑一個登入，避免 register 在壓測中佔用 DB。
        """
        user_id = random.randint(1, PRE_CREATED_USERS)
        self.username = f"testuser_{user_id}"
        self.password = "password123"
        self.auth_headers = {}
        self.last_order_id = None

        # 直接登入，不做 register
        resp = self.client.post(
            "/auth/login",
            data={
                "username": self.username,
                "password": self.password
            },
            name="/auth/login"
        )

        if resp.status_code == 200:
            token = resp.json()["access_token"]
            self.auth_headers = {"Authorization": f"Bearer {token}"}

    @task(5)
    def browse_and_buy(self):
        """
        真實用戶行為：先看商品列表，再下手搶購。
        這個 task 的 weight=5，被選中的機率最高。
        """
        # 先瀏覽商品列表
        self.client.get("/products", name="/products")

        # 再搶購
        with self.client.post(
            f"/flash-sale/buy/{TARGET_PRODUCT_ID}",
            json={"quantity": 1},
            headers=self.auth_headers,
            name="/flash-sale/buy",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                # 記錄 order_id，方便後續查狀態
                self.last_order_id = response.json().get("order_id")
            elif response.status_code == 400:
                # 庫存不足是預期行為，不算 failure
                response.success()

    @task(3)
    def just_buy(self):
        """
        直接搶購，不先瀏覽。模擬反應快的用戶或搶購腳本。
        weight=3，比 browse_and_buy 少一點。
        """
        with self.client.post(
            f"/flash-sale/buy/{TARGET_PRODUCT_ID}",
            json={"quantity": 1},
            headers=self.auth_headers,
            name="/flash-sale/buy",
            catch_response=True
        ) as response:
            if response.status_code == 400:
                response.success()

    @task(2)
    def check_stock(self):
        """查詢即時庫存（Redis）。純 read，壓力小。"""
        self.client.get(
            f"/products/{TARGET_PRODUCT_ID}/stock",
            name="/products/{id}/stock"
        )

    @task(1)
    def check_my_orders(self):
        """查詢我的訂單列表。需要 JWT Token。"""
        self.client.get(
            "/orders",
            headers=self.auth_headers,
            name="/orders"
        )
