import asyncio
import json
import logging
import random
import time
from http import HTTPMethod
from urllib.parse import unquote, urljoin

from aiohttp import ClientSession
from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest
from telethon.tl.types import InputPeerUser, InputUser, User

from .settings import BOT_ID, Settings


def full_name(user: User) -> str:
    return f"{user.first_name} {user.last_name or ''}"


class Clicker:
    def __init__(
        self,
        client: TelegramClient,
        aiohttp_session: ClientSession,
        user: User,
        settings: Settings,
        bot_access_hash: int | None = None,
    ) -> None:
        self.client = client
        self.aiohttp_session = aiohttp_session
        self.settings = settings
        self.base_url = "https://api.hamsterkombat.io"

        self._web_data: str | None = None
        self._auth_token: str | None = None
        self._bot_access_hash = bot_access_hash
        self._headers = {
            "Accept": "*/*",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Origin": "https://hamsterkombat.io/",
            "Referer": "https://hamsterkombat.io/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
            "sec-ch-ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
        }

        self._last_updating_time: int = int(time.time()) - 3600
        self._sync: dict = {}

        self._upgrades_for_buy: list[dict] = []
        self._balance: float = 0.0
        self._available_taps: int = 0

        self.logger = logging.getLogger(full_name(user))

    async def set_web_data(self) -> None:
        response = await self.client(
            RequestWebViewRequest(
                peer=InputPeerUser(BOT_ID, self._bot_access_hash),
                bot=InputUser(BOT_ID, self._bot_access_hash),
                platform="ios",
                url="https://hamsterkombat.io/",
            )
        )
        self._web_data = unquote(
            response.url.split("tgWebAppData=")[1].split("&tgWebAppVersion")[0]
        )

    async def _make_request(
        self, method: HTTPMethod, endpoint: str, data: dict | None = None
    ) -> dict:
        response = await self.aiohttp_session.request(
            method=method,
            url=urljoin(self.base_url, endpoint),
            headers=self._headers,
            data=json.dumps(data),
        )
        response_text = await response.text()
        try:
            return json.loads(response_text)
        except Exception as e:
            self.logger.error(
                "Failed to load response, response=%s, error=%s", response_text, e
            )

    async def set_auth_token(self) -> None:
        response_data = await self._make_request(
            HTTPMethod.POST,
            "/auth/auth-by-telegram-webapp",
            {"initDataRaw": self._web_data, "fingerprint": {}},
        )
        if auth_token := response_data.get("authToken"):
            self._auth_token = auth_token
            self._headers["Authorization"] = f"Bearer {self._auth_token}"
            return

        raise ValueError(f"Failed to get auth token, response: {response_data}")

    async def get_tasks(self) -> list[dict]:
        response = await self._make_request(
            HTTPMethod.POST,
            "/clicker/list-tasks",
        )
        return response["tasks"]

    async def check_task(self, task_id: str) -> dict:
        return await self._make_request(
            HTTPMethod.POST, "/clicker/check-task", {"taskId": task_id}
        )

    async def sync(self) -> dict | None:
        response_data = await self._make_request(
            HTTPMethod.POST,
            "/clicker/sync",
            {"timestamp": int(time.time())},
        )

        if response_data.get("found"):
            self._last_updating_time = response_data["found"]["clickerUser"][
                "lastSyncUpdate"
            ]
            return response_data["found"]["clickerUser"]

        elif clicker_user := response_data.get("clickerUser"):
            self._last_updating_time = response_data["clickerUser"]["lastSyncUpdate"]
            return clicker_user

        return None

    async def upgrades_for_buy(self) -> list[dict]:
        response_data = await self._make_request(
            HTTPMethod.POST,
            "/clicker/upgrades-for-buy",
        )
        return response_data["upgradesForBuy"]

    async def tap(self, available_taps: int, taps: int) -> dict | None:
        response_data = await self._make_request(
            HTTPMethod.POST,
            "/clicker/tap",
            {
                "count": taps,
                "availableTaps": available_taps,
                "timestamp": int(time.time()),
            },
        )

        if response_data.get("found"):
            return response_data["found"]["clickerUser"]

        elif clicker_user := response_data.get("clickerUser"):
            return clicker_user

        return None

    async def buy_upgrade(self, upgrade_id: str) -> dict:
        return await self._make_request(
            HTTPMethod.POST,
            "/clicker/buy-upgrade",
            {"upgradeId": upgrade_id, "timestamp": int(time.time())},
        )

    async def auth(self) -> None:
        await self.set_web_data()
        await self.set_auth_token()

    def _set_upgrades_for_buy(self, upgrades: list[dict]) -> None:
        self._upgrades_for_buy = [
            upgrade
            for upgrade in upgrades
            if upgrade["isAvailable"]
            and upgrade["isExpired"] is False
            and upgrade.get("cooldownSeconds", 0) == 0
        ]
        self._upgrades_for_buy.sort(
            key=lambda upgrade: upgrade["profitPerHourDelta"] / upgrade["price"],
            reverse=True,
        )

    async def _find_and_upgrade(self) -> None:
        if not self._upgrades_for_buy:
            self._set_upgrades_for_buy(await self.upgrades_for_buy())

        for upgrade in self._upgrades_for_buy:
            if self._balance >= upgrade["price"]:

                self.logger.info(
                    "Sleep 5 seconds before upgrade... upgrade_id=%s", upgrade["id"]
                )
                await asyncio.sleep(5)
                self.logger.info(
                    "Upgrade upgrade_id=%s, balance=%s, price=%s, profit_delta=%s",
                    upgrade["id"],
                    self._balance,
                    upgrade["price"],
                    upgrade["profitPerHourDelta"],
                )
                response = await self.buy_upgrade(upgrade["id"])

                if clicker_user := response.get("clickerUser"):
                    self.logger.info(
                        "Upgraded updrade_id=%s, balance=%s, profit_delta=%s",
                        upgrade["id"],
                        clicker_user["balanceCoins"],
                        upgrade["profitPerHourDelta"],
                    )
                    self._balance = clicker_user["balanceCoins"]

                else:
                    self.logger.info(
                        "Failed to upgrade, upgrade_id=%s, response=%s",
                        upgrade["id"],
                        response,
                    )

                if upgrade_for_buy := response.get("upgradesForBuy"):
                    self._set_upgrades_for_buy(
                        upgrade_for_buy
                    )  # update upgrades_for_buy cycle

            else:
                if self.settings.sleep_for_profitable:
                    self.logger.info(
                        "Not enough balance to upgrade most profitable, balance=%s, upgrade_id=%s, price=%s, profit_delta=%s",
                        self._balance,
                        upgrade["id"],
                        upgrade["price"],
                        upgrade["profitPerHourDelta"],
                    )
                    break

    async def start(self) -> None:
        self.logger.info("Starting clicker...")

        while True:
            try:
                if abs(self._last_updating_time - int(time.time())) >= 3600:
                    await self.auth()
                    self._sync = await self.sync()

                    self.logger.info(
                        "Synced, last_passive_earn=%s, earn_passive_per_hour=%s",
                        self._sync["lastPassiveEarn"],
                        self._sync["earnPassivePerHour"],
                    )
                    self._available_taps = self._sync["availableTaps"]
                    self._balance = self._sync["balanceCoins"]

                taps = random.randint(self.settings.min_taps, self.settings.max_taps)
                if (
                    taps > self._available_taps
                ):  # in case if available taps is less than random taps
                    taps = self._available_taps

                tap_response = await self.tap(self._available_taps, taps)

                available_taps = tap_response["availableTaps"]
                profit = tap_response["balanceCoins"] - self._balance
                self._balance = tap_response["balanceCoins"]

                self.logger.info(
                    "Tapped, taps=%s, profit=%s, balance=%s",
                    taps,
                    profit,
                    self._balance,
                )

                if self.settings.auto_upgrade:
                    await self._find_and_upgrade()

                if available_taps < self.settings.min_energy:
                    sleep_time = self._sync["maxTaps"] / self._sync["tapsRecoverPerSec"]
                    self.logger.info(
                        "Minimum available taps reached, available_taps=%s, sleep=%s",
                        available_taps,
                        sleep_time,
                    )
                    await asyncio.sleep(sleep_time)

                    continue

                sleep_time = random.randint(
                    self.settings.min_sleep_time, self.settings.max_sleep_time
                )

                self.logger.info("Sleeping... sleep_time=%s", sleep_time)
                await asyncio.sleep(sleep_time)
            except Exception as e:
                self.logger.error("Get error while clicking, error=%s", e)
