import asyncio
import os

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.utils import parse_phone

from bot.settings import read_settings


async def main():
    settings = read_settings()

    session_name = input("Enter session name: ").lower()

    client = TelegramClient(
        session=session_name,
        api_id=settings.api_id,
        api_hash=settings.api_hash,
    )
    await client.connect()

    phone = parse_phone(input("Enter phone number: "))
    if phone is None:
        print("Invalid phone number")
        return

    await client.send_code_request(phone)

    code = input("Enter code: ")
    try:
        await client.sign_in(phone=phone, code=code)
    except SessionPasswordNeededError:
        password = input("Enter 2FA password: ")
        await client.sign_in(phone=phone, password=password)

    print("Session created successfully")

    os.replace(f"{session_name}.session", f"./sessions/{session_name}.session")


asyncio.run(main())
