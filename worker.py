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

from app.setting import settings
from app.database import SessionLocal
from app.models import Order


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
    try:
        message = json.loads(body.decode("utf-8"))
        order_id = message["order_id"]
        log(f"收到訂單 #{order_id}，開始處理...")
    except (json.JSONDecodeError, KeyError) as e:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    db: Session = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()

        if not order:

            log(f"user {message.get('user_id', 'unknown')} 訂單 #{order_id} 不存在，丟棄訊息")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        if order.status != "pending":
            log(f"user {message.get('user_id', 'unknown')} 訂單 #{order_id} 狀態已是 {order.status}，跳過")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        order.status = "completed"
        db.commit()

        log(f"訂單 #{order_id} 處理完成 ✓")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        db.rollback()
        log(f"訂單 #{order_id} 處理失敗，放回 queue：{e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    finally:
        db.close()


def start_worker():
    """
    啟動 Worker，持續監聽 RabbitMQ
    包含斷線重連邏輯
    """
    log("Worker 啟動中...")

    while True:  
        try:
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_USER,
                settings.RABBITMQ_PASSWORD
            )
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=settings.RABBITMQ_HOST,
                    port=settings.RABBITMQ_PORT,
                    credentials=credentials,
                    heartbeat=60,
                )
            )
            channel = connection.channel()

            channel.queue_declare(
                queue=settings.RABBITMQ_QUEUE_FLASH_SALE, durable=True)

            channel.basic_qos(prefetch_count=1)

            channel.basic_consume(
                queue=settings.RABBITMQ_QUEUE_FLASH_SALE,
                on_message_callback=process_order
            )

            log("等待訂單訊息中...（按 Ctrl+C 停止）")
            channel.start_consuming()  

        except pika.exceptions.AMQPConnectionError:
            log("RabbitMQ 連線失敗，5 秒後重試...")
            time.sleep(5)

        except KeyboardInterrupt:
            log("Worker 已停止")
            break


if __name__ == "__main__":
    start_worker()
