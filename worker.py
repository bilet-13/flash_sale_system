"""
Worker - 背景訂單處理程序

職責：監聽 RabbitMQ 的 flash_sale_orders queue
      收到訊息後，把訂單狀態從 pending 改成 completed

啟動方式：python worker.py（獨立於 FastAPI 運行）
"""
import json
import time
import pika
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Order


# ──────────────────────────────────────────
# TODO 1：改成你喜歡的 log 格式
# 現在的格式是：[WORKER] 這是一條訊息
# 你可以改成：🔧 這是一條訊息  或  2024-01-01 WORKER: 這是一條訊息
# ──────────────────────────────────────────
import datetime


def log(message: str):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[WORKER] {now} {message}")


def process_order(ch, method, properties, body):
    """
    處理單一訂單訊息

    這個 function 是 RabbitMQ 的 callback：
    每次 queue 裡有新訊息，RabbitMQ 就會自動呼叫這個 function

    參數說明（RabbitMQ 自動傳入，不需要我們自己呼叫）：
      ch         - channel，用來傳 ack
      method     - 訊息的 metadata（包含 delivery_tag，ack 用的）
      properties - 訊息的屬性（我們沒用到）
      body       - 訊息內容（bytes，需要 decode）
    """
    # Step 1: 解析訊息
    # body 是 bytes，所以要先 decode 成字串，再用 json.loads 轉成 dict
    try:
        message = json.loads(body.decode("utf-8"))
        order_id = message["order_id"]
        log(f"收到訂單 #{order_id}，開始處理...")
    except (json.JSONDecodeError, KeyError) as e:
        # 訊息格式壞掉了，這條訊息沒救了
        # nack + requeue=False 代表：不重試，直接丟掉
        # 為什麼不重試？因為格式本身就壞了，重試 100 次也是壞的
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    # Step 2: 更新資料庫訂單狀態
    db: Session = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()

        if not order:
            # 訂單不存在（不太可能，但要處理）
            # ──────────────────────────────────────────
            # TODO 2：改這裡的 log 訊息
            # 現在寫的是「訂單不存在」，試著加上更多資訊
            # 例如：把 message 裡的 user_id 也印出來
            # ──────────────────────────────────────────

            log(f"user {message.get('user_id', 'unknown')} 訂單 #{order_id} 不存在，丟棄訊息")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        if order.status != "pending":
            # 已經處理過了（可能是重複訊息）
            # 直接 ack，避免重複處理
            # 為什麼會有重複訊息？網路問題導致 ack 沒送到 RabbitMQ，它就重新發送
            log(f"user {message.get('user_id', 'unknown')} 訂單 #{order_id} 狀態已是 {order.status}，跳過")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # 核心操作：把狀態改成 completed
        order.status = "completed"
        db.commit()

        log(f"訂單 #{order_id} 處理完成 ✓")

        # Step 3: 告訴 RabbitMQ 這條訊息處理好了，可以從 queue 移除
        # 為什麼要 ack？
        # 如果不 ack，RabbitMQ 會以為這條訊息還沒被處理
        # worker 重啟後會再次收到同一條訊息（重複處理）
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        db.rollback()
        # nack + requeue=True 代表：處理失敗，放回 queue 等等再試
        # 為什麼這裡要重試？因為可能是暫時性的 DB 連線問題
        log(f"訂單 #{order_id} 處理失敗，放回 queue：{e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    finally:
        # 不管成功或失敗，都要關掉 DB 連線
        # 為什麼要關？連線是有限資源，不關會耗盡連線池
        db.close()


def start_worker():
    """
    啟動 Worker，持續監聽 RabbitMQ
    包含斷線重連邏輯
    """
    log("Worker 啟動中...")

    while True:  # 外層 while：斷線後重新連接
        try:
            # 連接 RabbitMQ
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_USER,
                settings.RABBITMQ_PASSWORD
            )
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOST,
                    port=settings.RABBITMQ_PORT,
                    credentials=credentials,
                    # heartbeat：每 60 秒跟 RabbitMQ 確認連線還活著
                    # 如果沒有這個，長時間沒訊息時連線會被切斷
                    heartbeat=60,
                )
            )
            channel = connection.channel()

            # 宣告 queue（跟 flash_sale.py 裡的名字一定要一樣！）
            # durable=True：RabbitMQ 重啟後 queue 不消失
            channel.queue_declare(queue=settings.RABBITMQ_QUEUE_FLASH_SALE, durable=True)

            # prefetch_count=1：一次只處理 1 條訊息
            # 為什麼？確保處理完才拿下一條，不會同時處理太多
            channel.basic_qos(prefetch_count=1)

            # 註冊 callback：有訊息進來就呼叫 process_order
            channel.basic_consume(
                queue=settings.RABBITMQ_QUEUE_FLASH_SALE,
                on_message_callback=process_order
            )

            log("等待訂單訊息中...（按 Ctrl+C 停止）")
            channel.start_consuming()  # 開始監聽（這行會 block，不會往下跑）

        except pika.exceptions.AMQPConnectionError:
            # RabbitMQ 連不上（可能還在啟動中）
            # ──────────────────────────────────────────
            # TODO 3：改這裡的等待秒數
            # 現在是等 5 秒後重試，你覺得改成幾秒比較好？
            # 想想看：太短有什麼問題？太長有什麼問題？
            # ──────────────────────────────────────────
            log("RabbitMQ 連線失敗，5 秒後重試...")
            time.sleep(5)

        except KeyboardInterrupt:
            log("Worker 已停止")
            break


if __name__ == "__main__":
    start_worker()
