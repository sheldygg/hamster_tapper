import asyncio
import os

from telethon import TelegramClient

from bot.settings import read_settings


async def main():
    settings = read_settings()

    session_name = input("Enter session name: ")
    client = TelegramClient(
        session=session_name,
        api_id=settings.api_id,
        api_hash=settings.api_hash,
    )
    await client.start()
    await client.disconnect()

    os.replace(f"{session_name}.session", f"./sessions/{session_name}.session")


asyncio.run(main())
