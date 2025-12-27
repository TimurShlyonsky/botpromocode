import os
from telethon import TelegramClient

API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")
CHANNEL = os.getenv("TG_CHANNEL")  # без @

def test_read_channel(limit: int = 5):
    with TelegramClient("promo_session", API_ID, API_HASH) as client:
        channel = client.get_entity(CHANNEL)

        for message in client.iter_messages(channel, limit=limit):
            if message.text:
                print("-----")
                print(message.text)
