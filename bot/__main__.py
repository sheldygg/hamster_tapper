import asyncio
import json
import logging

from pathlib import Path

from aiohttp import ClientSession
from telethon import TelegramClient
from telethon.errors.rpcerrorlist import FloodWaitError
from telethon.custom import Dialog

from .clicker import Clicker
from .settings import Settings, read_settings, BOT_ID


def get_sessions() -> list[Path]:
    sessions = Path().glob("sessions/*.session")
    return [session for session in sessions]


async def get_access_hash(client: TelegramClient, user_id: int) -> int:
    try:
        bot_peer = await client.get_input_entity("hamster_kombat_bot")
        return bot_peer.access_hash
    except FloodWaitError:
        dialog: Dialog
        async for dialog in client.iter_dialogs():
            if dialog.id == BOT_ID:
                return dialog.entity.access_hash

    raise RuntimeError(f"Failed to get access hash for {user_id}")


async def create_clicker_instances(
    aiohttp_session: ClientSession,
    access_hashes: dict,
    settings: Settings,
) -> list[Clicker]:
    clicker_instances = []

    sessions = get_sessions()
    for session in sessions:
        client = TelegramClient(
            session=session,
            api_id=settings.api_id,
            api_hash=settings.api_hash,
        )
        await client.connect()
        me = await client.get_me()

        access_hash = access_hashes.get(str(me.id))
        if not access_hash:
            try:
                access_hash = await get_access_hash(client, me.id)
                access_hashes[me.id] = access_hash
            except RuntimeError as e:
                print(e)

        clicker = Clicker(
            client=client,
            aiohttp_session=aiohttp_session,
            user=me,
            settings=settings,
            bot_access_hash=access_hash
        )
        clicker_instances.append(clicker)

    return clicker_instances


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    aiohttp_session = ClientSession()

    with open("access_hashes.json", "r") as access_hashes_file:
        access_hashes = json.loads(access_hashes_file.read())

    settings = read_settings()

    clicker_instances = await create_clicker_instances(aiohttp_session, access_hashes, settings)

    try:
        await asyncio.gather(*[clicker.start() for clicker in clicker_instances])
    finally:
        await aiohttp_session.close()

        with open("access_hashes.json", "w") as file:
            json.dump(access_hashes, file, indent=4)


asyncio.run(main())
