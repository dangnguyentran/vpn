import json
import asyncio
from time import time
from random import randint
from urllib.parse import unquote

import aiohttp
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestWebView

from bot.config import settings
from bot.utils import logger
from bot.utils.scripts import escape_html, is_jwt_valid
from bot.exceptions import InvalidSession


headers = {
    'accept': '*/*',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'content-type': 'application/json',
    'origin': 'https://alohomora-bucket-fra1-prod-frontend-static.fra1.cdn.digitaloceanspaces.com',
    'priority': 'u=1, i',
    'referer': 'https://alohomora-bucket-fra1-prod-frontend-static.fra1.cdn.digitaloceanspaces.com/',
    'sec-ch-ua': '"Android WebView";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'user-agent': 'Mozilla/5.0 (Linux; Android 13; M2101K6G Build/TKQ1.221013.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/125.0.6422.165 Mobile Safari/537.36',
    'x-requested-with': 'org.telegram.messenger'
}


class Tapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client

    async def get_tg_web_data(self) -> str:
        try:
            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            dialogs = self.tg_client.get_dialogs()
            async for dialog in dialogs:
                if dialog.chat and dialog.chat.username and dialog.chat.username == 'wcoin_tapbot':
                    break

            while True:
                try:
                    peer = await self.tg_client.resolve_peer('wcoin_tapbot')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"{self.session_name} | FloodWait {fl}")
                    fls *= 2
                    logger.info(f"{self.session_name} | Sleep {fls}s")

                    await asyncio.sleep(fls)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=peer,
                bot=peer,
                platform='android',
                from_bot_menu=False,
                url='https://starfish-app-fknmx.ondigitalocean.app/alohomora/'
            ))

            auth_url = web_view.url
            tg_web_data = unquote(
                string=unquote(
                    string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0]))

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(
                f"{self.session_name} | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=3)

    async def login(self, http_client: aiohttp.ClientSession, base_url: str, user_id: str) -> dict:
        response_text = ''
        try:
            response = await http_client.post(url=base_url, json={"identifier": user_id, "password": user_id})
            response_text = await response.text()
            response.raise_for_status()
            response_json = await response.json()
            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while getting Access Token: {error} | "
                         f"Response text: {escape_html(response_text)[:256]}...")
            await asyncio.sleep(delay=3)

    async def get_me_telegram(self, http_client: aiohttp.ClientSession, url: str) -> dict:
        response_text = ''
        try:
            response = await http_client.get(url=url)
            response_text = await response.text()
            response.raise_for_status()

            response_json = await response.json()
            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while getting Me Telegram: {error} | "
                         f"Response text: {escape_html(response_text)[:256]}...")
            await asyncio.sleep(delay=3)

    async def send_taps(self, http_client: aiohttp.ClientSession, url: str, data: dict) -> dict:
        response_text = ''
        try:
            enc_response = await http_client.post(url="https://aesthetic-lainey-aassi-5c0d59d9.koyeb.app/encrypt", json={"dataToEncrypt": data})
            enc_response_json = await enc_response.json()
            enc_json = enc_response_json["encryptedData"]
            enc_json['data'] = data
            response = await http_client.put(url=url, json=enc_json)
            response_text = await response.text()
            if response.status != 422:
                response.raise_for_status()

            response_json = json.loads(response_text)
            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while Tapping: {error} | "
                         f"Response text: {escape_html(response_text)[:512]}...")
            await asyncio.sleep(delay=3)

    async def run(self) -> None:
        access_token = ''
        user_data = {}
        async with aiohttp.ClientSession(headers=headers) as http_client:

            tg_web_data = await self.get_tg_web_data()
            user_id = tg_web_data.split('"id":')[1].split(',')[0].strip()
            query_id = tg_web_data.split('query_id=', maxsplit=1)[1].split('&user', maxsplit=1)[0]
            user_details = tg_web_data.split('user=', maxsplit=1)[1].split('&auth_date', maxsplit=1)[0]
            auth_date = tg_web_data.split('auth_date=', maxsplit=1)[1].split('&hash', maxsplit=1)[0]
            hash_ = tg_web_data.split('hash=', maxsplit=1)[1]

            base_url = f'https://starfish-app-fknmx.ondigitalocean.app/wapi/api/auth/local?hash=query_id={query_id}&user={user_details}&auth_date={auth_date}&hash={hash_}'
            get_me_details_url = f'https://starfish-app-fknmx.ondigitalocean.app/wapi/api/users/me?timestamp={int(time())}&hash=query_id={query_id}&user={user_details}&auth_date={auth_date}&hash={hash_}'

            while True:
                try:
                    if not is_jwt_valid(access_token):
                        # Remove Authorization header conditionally
                        if "Authorization" in http_client.headers:
                            del http_client.headers["Authorization"]
                        login_data = await self.login(http_client=http_client, base_url=base_url, user_id=user_id)
                        user_data = login_data['user']
                        access_token = login_data['jwt']

                        if not access_token:
                            logger.error(
                                f"{self.session_name} | Failed fetch token | Sleep {60}s")
                            await asyncio.sleep(delay=60)
                            continue

                    new_energy = (int(time()) - int(user_data["last_click_at"])) * (
                        int(user_data["energy_refill_multiplier"]) + 1) + int(user_data["energy"])
                    if new_energy > int(user_data["max_energy"]):
                        new_energy = int(user_data["max_energy"])
                    user_data["energy"] = new_energy

                    logger.info(
                        f"{self.session_name} | Updated Energy value |(<g>{int(user_data['energy']):,}</g>)")

                    http_client.headers["Authorization"] = f"Bearer {access_token}"
                    if not user_data:
                        user_data = await self.get_me_telegram(http_client=http_client, url=get_me_details_url)

                    if int(user_data["energy"]) < settings.MIN_AVAILABLE_ENERGY:
                        random_sleep = randint(
                            settings.SLEEP_BY_MIN_ENERGY[0], settings.SLEEP_BY_MIN_ENERGY[1])
                        logger.info(
                            f"{self.session_name} | energy is zero | Sleep {random_sleep}s")
                        await asyncio.sleep(delay=random_sleep)
                        continue

                    random_taps = randint(a=20, b=80)
                    if int(user_data["energy"]) < random_taps:
                        random_taps = int(user_data["energy"])

                    tap_data = {
                        "id": user_data["id"],
                        "clicks": int(user_data["clicks"]) + random_taps,
                        "energy": int(user_data["energy"]) - random_taps,
                        "balance": int(user_data['balance']) + random_taps,
                        "balance_from_clicks": int(user_data["balance_from_clicks"]) + random_taps,
                        "last_click_at": int(time()),
                    }

                    send_taps_url = f'https://starfish-app-fknmx.ondigitalocean.app/wapi/api/users/{user_data["id"]}?timestamp={int(time())}&hash=query_id={query_id}&user={user_details}&auth_date={auth_date}&hash={hash_}'

                    response = await self.send_taps(http_client=http_client, url=send_taps_url, data=tap_data)

                    logger.success(f"{self.session_name} | Successful tapped! | "
                                   f"Balance: <c>{int(user_data['balance']):,}</c> (<g>+{int(random_taps):,}</g>) | Total: <e>{int(response['balance']):,}</e>")

                    user_data.clear()
                    user_data.update(response)
                except InvalidSession as error:
                    raise error

                except Exception as error:
                    logger.error(f"{self.session_name} | Unknown error: {error}")
                    await asyncio.sleep(delay=3)

                else:
                    sleep_between_clicks = randint(
                        a=settings.SLEEP_BETWEEN_TAP[0], b=settings.SLEEP_BETWEEN_TAP[1])
                    logger.info(f"Sleep {sleep_between_clicks}s")
                    await asyncio.sleep(delay=sleep_between_clicks)


async def run_tapper(tg_client: Client):
    try:
        await Tapper(tg_client=tg_client).run()
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
