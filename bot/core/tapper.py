import asyncio
import json
import random
import sys
import traceback
from itertools import cycle
from urllib.parse import unquote

import aiohttp
import requests
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.types import InputBotAppShortName
from pyrogram.raw.functions.messages import RequestAppWebView
from bot.core.agents import generate_random_user_agent
from bot.config import settings
import time as time_module

from bot.utils import logger
from bot.exceptions import InvalidSession
from .headers import headers
from random import randint
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)




class Tapper:
    def __init__(self, tg_client: Client, multi_thread: bool):
        self.tg_client = tg_client
        self.session_name = tg_client.name
        self.first_name = ''
        self.last_name = ''
        self.user_id = ''
        self.auth_token = ""
        self.last_claim = None
        self.last_checkin = None
        self.balace = 0
        self.maxtime = 0
        self.fromstart = 0
        self.new_usr = False
        self.balance = 0
        self.multi_thread = multi_thread
        self.my_ref = "frndId6493211155"
        self.ref = "frndId6493211155"
        self.coin_earn_per_tap = 0
        self.available_energy = 0
        self.set_user = True
        self.max_energy = 0

    async def get_tg_web_data(self, proxy: str | None) -> str:
        try:
            if settings.REF_LINK == "":
                ref_param = "frndId6493211155"
            else:
                ref_param = settings.REF_LINK.split("=")[1]
        except:
            logger.error(f"{self.session_name} | Ref link invaild please check again !")
            sys.exit()
        actual = random.choices([self.my_ref, ref_param], weights=[30, 70]) # edit this line to [0, 100] if you don't want to support me
        self.ref = actual[0]
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict
        try:
            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            while True:
                try:
                    peer = await self.tg_client.resolve_peer('battle_games_com_bot')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"<light-yellow>{self.session_name}</light-yellow> | FloodWait {fl}")
                    logger.info(f"<light-yellow>{self.session_name}</light-yellow> | Sleep {fls}s")

                    await asyncio.sleep(fls + 3)

            web_view = await self.tg_client.invoke(RequestAppWebView(
                peer=peer,
                app=InputBotAppShortName(bot_id=peer, short_name="start"),
                platform='android',
                write_allowed=True,
                start_param=actual[0]
            ))

            auth_url = web_view.url
            # print(auth_url)
            tg_web_data = unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])
            # print(tg_web_data)

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Unknown error during Authorization: "
                         f"{error}")
            await asyncio.sleep(delay=3)

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy):
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5), )
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
            return True
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")
            return False

    async def join_channel(self):
        try:
            logger.info(f"{self.session_name} | Joining TG channel...")
            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)
            try:
                await self.tg_client.join_chat("battle_games_com")
                logger.success(f"{self.session_name} | <green>Joined channel successfully</green>")
            except Exception as e:
                logger.error(f"{self.session_name} | <red>Join TG channel failed - Error: {e}</red>")

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

        except Exception as error:
            logger.error(f"<light-yellow>{self.session_name}</light-yellow> | Unknown error during Authorization: "
                         f"{error}")
            await asyncio.sleep(delay=3)

    def login(self, session: requests.Session):
        response = session.post(f"https://api.battle-games.com:8443/api/api/v1/user?inviteCode={self.ref}", headers=headers)
        if response.status_code == 200:
            for cookie in response.cookies:
                session.cookies.set(cookie.name, cookie.value)
            logger.success(f"{self.session_name} | <green>Logged in.</green>")
            return True
        else:
            print(response.json())
            logger.warning("{self.session_name} | <red>Failed to login</red>")
            return False

    def do_checkin_task(self, session: requests.Session):
        res = session.post("https://api.battle-games.com:8443/api/api/v1/tasks/streak_days/complete", headers=headers)
        if res.status_code == 200:
            logger.success(f"{self.session_name} | <green>Checked in successfully!</green>")
        else:
            print(res.text)
            logger.warning(f"{self.session_name} | <yellow>Failed to check in: {res.status_code}</yellow>")

    def get_user_info(self, session: requests.Session):
        res = session.post("https://api.battle-games.com:8443/api/api/v1/user/sync", headers=headers)
        if res.status_code == 200:
            data_ = res.json()['data']
            self.max_energy = data_['maxEnergy']
            self.available_energy = data_['availableEnergy']
            self.coin_earn_per_tap = data_['earnCoinsPerTap']
            logger.info(f"{self.session_name} | Balance: <yellow>{data_['balance']}</yellow> | Total earned: <light-yellow>{data_['totalCoins']}</light-yellow>")
        else:
            print(res.text)
            logger.warning(f"{self.session_name} | <yellow>Failed to get user info: {res.status_code}</yellow>")

    def sync(self, session: requests.Session):
        res = session.post("https://api.battle-games.com:8443/api/api/v1/user/sync", headers=headers)
        if res.status_code == 200:
            data_ = res.json()['data']
            self.max_energy = data_['maxEnergy']
            self.available_energy = data_['availableEnergy']
            self.coin_earn_per_tap = data_['earnCoinsPerTap']
            self.balance = data_['balance']
        else:
            print(res.text)
            logger.warning(f"{self.session_name} | <yellow>Failed to get user info: {res.status_code}</yellow>")

    def set_block_chain(self, session: requests.Session):
        payload = {
            "blockchainId": "bitcoin"
        }
        res = session.put("https://api.battle-games.com:8443/api/api/v1/user/blockchain", headers=headers, json=payload)
        if res.status_code == 200:
            self.sync(session)
        else:
            print(res.text)
            logger.warning(f"{self.session_name} | <yellow>Failed to set blockchain: {res.status_code}</yellow>")

    def complete_task(self, session: requests.Session, task_id):
        if task_id == "set_telegram_username" and self.set_user is False:
            return
        res = session.post(f"https://api.battle-games.com:8443/api/api/v1/tasks/{task_id}/complete", headers=headers)
        if res.status_code == 200:
            logger.success(f"{self.session_name} | <green>Successfully completed task: {task_id}</green>")
        else:
            if task_id == "set_telegram_username":
                self.set_user = False
                logger.warning(f"{self.session_name} | <yellow>YOU MUST SET TELEGRAM USERNAME TO COMPLETE {task_id}!</yellow>")
            else:
                print(res.text)
                logger.warning(f"{self.session_name} | <yellow>Failed to complete {task_id}: {res.status_code}</yellow>")

    async def do_tasks(self, session: requests.Session):
        res = session.get("https://api.battle-games.com:8443/api/api/v1/tasks", headers=headers)
        if res.status_code == 200:
            tasks = res.json()['data']
            for task in tasks:
                if task['id'] == "invite_new_friends_rep_10" or task['completedAt'] is not None:
                    continue
                elif task['id'] == "select_blockchain":
                    self.set_block_chain(session)
                    self.complete_task(session, task['id'])
                elif task['id'] == "subscribe_telegram_channel":
                    await self.join_channel()
                    self.complete_task(session, task['id'])
                elif task['id']:
                    self.complete_task(session, task['id'])
                await asyncio.sleep(random.uniform(3, 6))
        else:
            print(res.text)
            logger.warning(f"{self.session_name} | <yellow>Failed to get tasks info: {res.status_code}</yellow>")

    def tap(self, session: requests.Session, taps: int):
        time = int(time_module.time())*1000
        payload = {
            "availableEnergy": int(self.available_energy) - taps + randint(0, taps-randint(0, taps - 1)),
            "requestedAt": time,
            "taps": taps
        }
        res = session.post("https://api.battle-games.com:8443/api/api/v1/taps", headers=headers, json=payload)
        if res.status_code == 200:
            res_d = res.json()
            logger.success(f"{self.session_name} | Successfully tapped <cyan>{taps}</cyan> times | Balance: <yellow>{res_d['data']['balance']}</yellow>")
        else:
            print(res.text)
            logger.warning(f"{self.session_name} | <yellow>Failed to tap: {res.status_code}</yellow>")

    def upgrade_card(self, card, session: requests.Session):
        timel = int(time_module.time()) * 1000
        payload = {
            "cardId": card['id'],
            "requestedAt": timel
        }
        res = session.post("https://api.battle-games.com:8443/api/api/v1/cards/buy", json=payload, headers=headers)
        if res.status_code == 200:
            logger.success(
                f"{self.session_name} | <green>Successfully upgraded card: <cyan>{card['id']}</cyan> - Cost: <yellow>{card['nextLevel']['cost']}</yellow></green>")
            return True
        else:
            logger.warning(f"{self.session_name} | <yellow>Failed to upgrade {card['id']}: {res.status_code}</yellow>")
            return False

    async def upgrade(self, session: requests.Session):
        can_upgrade = True
        while can_upgrade:
            self.sync(session)
            can_upgrade = False
            res = session.get("https://api.battle-games.com:8443/api/api/v1/cards", headers=headers)
            if res.status_code == 200:
                logger.info(f"{self.session_name} | Get card info successfully!")
                cards = res.json()['data']
                best_available_cards = []
                available_cards = []
                for card in cards:
                    if card['boughtAt'] is not None:
                        if int(time_module.time())*1000 < card['boughtAt'] + card['rechargingDuration']:
                            continue
                    if card['condition'] is None and int(self.balance) >= int(card['nextLevel']['cost']) or card['condition']['passed'] and int(self.balance) >= int(card['nextLevel']
                    ['cost']):
                        available_cards.append(card)

                for card in available_cards:
                    profitable = card['nextLevel']['cost'] / card['nextLevel']['profitPerHour']
                    best_available_cards.append({
                        "profit": profitable,
                        "info": card
                    })

                best_to_upgrade = sorted(best_available_cards, key=lambda x: x['profit'])
                for card in best_to_upgrade:
                    can_upgrade = self.upgrade_card(card['info'], session)
                    break

            else:
                can_upgrade = False
                print(res.text)
                logger.warning(f"{self.session_name} | <yellow>Failed to get cards info: {res.status_code}</yellow>")
            await asyncio.sleep(randint(1, 5))

    async def redeem_promocodes(self, session: requests.Session):
        with open('code.json', 'r') as file:
            code_data = json.load(file)
        for code in settings.CODES:
            if code not in code_data.keys():
                payload = {
                    "code": code
                }
                res = session.post("https://api.battle-games.com:8443/api/api/v1/codes/redeem", headers=headers, json=payload)
                if res.status_code == 200:
                    logger.success(f"{self.session_name} | <green>Successfully redeemed code: {code}</green>")
                    code_data.update({code: True})
                    with open('code.json', 'w') as file:
                        json.dump(code_data, file, indent=4)
                else:
                    if res.status_code == 400:
                        code_data.update({code: True})
                        with open('code.json', 'w') as file:
                            json.dump(code_data, file, indent=4)
                    else:
                        print(res.text)
                        logger.warning(
                            f"{self.session_name} | <yellow>Failed to redeem code {code}. Status code:{res.status_code}</yellow>")

            await asyncio.sleep(randint(1, 5))



    async def run(self, proxy: str | None) -> None:
        access_token_created_time = 0
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        headers["User-Agent"] = generate_random_user_agent(device_type='android', browser_type='chrome')
        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        session = requests.Session()

        if proxy:
            proxy_check = await self.check_proxy(http_client=http_client, proxy=proxy)
            if proxy_check:
                proxy_type = proxy.split(':')[0]
                proxies = {
                    proxy_type: proxy
                }
                session.proxies.update(proxies)
                logger.info(f"{self.session_name} | bind with proxy ip: {proxy}")


        token_live_time = randint(3000, 3600)
        while True:
            try:
                if time_module.time() - access_token_created_time >= token_live_time:
                    tg_web_data = await self.get_tg_web_data(proxy=proxy)
                    # print(tg_web_data)
                    headers['Authorization'] = tg_web_data
                    access_token_created_time = time_module.time()
                    token_live_time = randint(3000, 3600)

                if self.login(session):
                    self.get_user_info(session)

                    if settings.AUTO_APPLY_PROMOCODES:
                        await self.redeem_promocodes(session)

                    if settings.AUTO_TASK:
                        await self.do_tasks(session)

                    if settings.AUTO_TAP:
                        n = randint(7, 15)
                        while n > 0:
                            n -= 1
                            taps = randint(settings.TAP_COUNTS[0], settings.TAP_COUNTS[1])
                            self.tap(session, taps)
                            sleep_ = int(taps / 3) + 1 + randint(1, 5)
                            logger.info(f"{self.session_name} | Sleep {sleep_}s...")
                            await asyncio.sleep(sleep_)

                    if settings.AUTO_UPGRADE:
                        self.sync(session)
                        await self.upgrade(session)


                if self.multi_thread:
                    sleep_ = randint(settings.SLEEP_TIME_BETWEEN_EACH_ROUND[0], settings.SLEEP_TIME_BETWEEN_EACH_ROUND[1])
                    logger.info(f"{self.session_name} | Sleep {sleep_}s...")
                    await asyncio.sleep(sleep_)
                else:
                    await http_client.close()
                    session.close()
                    break
            except InvalidSession as error:
                raise error

            except Exception as error:
                traceback.print_exc()
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=randint(60, 120))


async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        sleep_ = randint(1, 15)
        logger.info(f"{tg_client.name} | start after {sleep_}s")
        await asyncio.sleep(sleep_)
        await Tapper(tg_client=tg_client, multi_thread=True).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")


async def run_tapper1(tg_clients: list[Client], proxies):
    proxies_cycle = cycle(proxies) if proxies else None
    while True:
        for tg_client in tg_clients:
            try:
                await Tapper(tg_client=tg_client, multi_thread=False).run(
                    next(proxies_cycle) if proxies_cycle else None)
            except InvalidSession:
                logger.error(f"{tg_client.name} | Invalid Session")

            sleep_ = randint(settings.DELAY_EACH_ACCOUNT[0], settings.DELAY_EACH_ACCOUNT[1])
            logger.info(f"Sleep {sleep_}s...")
            await asyncio.sleep(sleep_)

        sleep_ = randint(settings.SLEEP_TIME_BETWEEN_EACH_ROUND[0], settings.SLEEP_TIME_BETWEEN_EACH_ROUND[1])
        logger.info(f"<red>Sleep {sleep_}s...</red>")
        await asyncio.sleep(sleep_)
