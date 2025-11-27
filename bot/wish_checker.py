import time
import requests
import os
import sys

# чтобы работал import webapp.db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from webapp.db import get_due_wishes, cancel_wish, get_telegram_id

BOT_TOKEN = "8332054798:AAGLpizBXxlQ2A4ByeE-L-aV5Ginm3mHkPw"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def send_message(chat_id, text):
    try:
        resp = requests.post(API_URL, data={
            "chat_id": chat_id,
            "text": text
        }, timeout=5)
        print("SEND STATUS:", resp.status_code, resp.text)
    except Exception as e:
        print("Ошибка отправки:", e)


def check_wishes():
    while True:
        due = get_due_wishes()
        print("Найдено напоминаний:", len(due))

        for wish_id, user_id, item in due:
            chat_id = get_telegram_id(user_id)
            if not chat_id:
                print(f"У user_id={user_id} нет telegram_id, пропускаю")
                continue

            send_message(chat_id, f"🔔 Напоминание!\nТы хотел купить: {item}")
            cancel_wish(wish_id, user_id)

        time.sleep(30)


if __name__ == "__main__":
    check_wishes()
