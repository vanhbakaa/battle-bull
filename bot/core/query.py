import asyncio
import json
import random
from itertools import cycle

import aiohttp
import requests
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
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
    def __init__(self, query: str, session_name, multi_thread):
        self.query = query
        self.session_name = session_name
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
        self.other_ref = settings.REF_LINK.split('=')[1]
        self.ref = random.choices([self.my_ref, self.other_ref], weights=[30, 70]) # edit this line to [0, 100] if you don't want to support me
        self.coin_earn_per_tap = 0
        self.available_energy = 0
        self.set_user = True
        self.max_energy = 0

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy):
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5), )
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
            return True
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")
            return False
    def login(self, session: requests.Session):
        response = session.post(f"https://api.battle-games.com:8443/api/api/v1/user?inviteCode={self.ref}",
                                headers=headers)
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
            logger.info(
                f"{self.session_name} | Balance: <yellow>{data_['balance']}</yellow> | Total earned: <light-yellow>{data_['totalCoins']}</light-yellow>")
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
                logger.warning(
                    f"{self.session_name} | <yellow>YOU MUST SET TELEGRAM USERNAME TO COMPLETE {task_id}!</yellow>")
            else:
                print(res.text)
                logger.warning(
                    f"{self.session_name} | <yellow>Failed to complete {task_id}: {res.status_code}</yellow>")

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
                    logger.warning(f"{self.session_name} | <yellow>Can't complete join telegram channel while running with query!</yellow>")
                elif task['id']:
                    self.complete_task(session, task['id'])
                await asyncio.sleep(random.uniform(3, 6))
        else:
            print(res.text)
            logger.warning(f"{self.session_name} | <yellow>Failed to get tasks info: {res.status_code}</yellow>")

    def tap(self, session: requests.Session, taps: int):
        time = int(time_module.time()) * 1000
        payload = {
            "availableEnergy": int(self.available_energy) - taps + randint(0, taps - randint(0, taps - 1)),
            "requestedAt": time,
            "taps": taps
        }
        res = session.post("https://api.battle-games.com:8443/api/api/v1/taps", headers=headers, json=payload)
        if res.status_code == 200:
            res_d = res.json()
            logger.success(
                f"{self.session_name} | Successfully tapped <cyan>{taps}</cyan> times | Balance: <yellow>{res_d['data']['balance']}</yellow>")
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
        else:
            print(res.text)
            logger.warning(f"{self.session_name} | <yellow>Failed to upgrade {card['id']}: {res.status_code}</yellow>")

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
                        if time_module.time() < card['boughtAt'] + card['rechargingDuration']:
                            continue
                    if card['condition'] is None or card['condition']['passed'] and self.balance >= card['nextLevel'][
                        'cost']:
                        available_cards.append(card)

                for card in available_cards:
                    profitable = card['nextLevel']['cost'] / card['nextLevel']['profitPerHour']
                    best_available_cards.append({
                        "profit": profitable,
                        "info": card
                    })

                best_to_upgrade = sorted(best_available_cards, key=lambda x: x['profit'])
                for card in best_to_upgrade:
                    self.upgrade_card(card['info'], session)
                    can_upgrade = True
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
                res = session.post("https://api.battle-games.com:8443/api/api/v1/codes/redeem", headers=headers,
                                   json=payload)
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
                    tg_web_data = self.query
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
                    sleep_ = randint(settings.SLEEP_TIME_BETWEEN_EACH_ROUND[0],
                                     settings.SLEEP_TIME_BETWEEN_EACH_ROUND[1])
                    logger.info(f"{self.session_name} | Sleep {sleep_}s...")
                    await asyncio.sleep(sleep_)
                else:
                    await http_client.close()
                    session.close()
                    break
            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=randint(60, 120))

async def run_query_tapper(query: str, name: str, proxy: str | None):
    try:
        sleep_ = randint(1, 15)
        logger.info(f" start after {sleep_}s")
        # await asyncio.sleep(sleep_)
        await Tapper(query=query, session_name=name, multi_thread=True).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"Invalid Query: {query}")

async def run_query_tapper1(querys: list[str], proxies):
    proxies_cycle = cycle(proxies) if proxies else None
    name = "Account"

    while True:
        i = 0
        for query in querys:
            try:
                await Tapper(query=query,session_name=f"{name} {i}",multi_thread=False).run(next(proxies_cycle) if proxies_cycle else None)
            except InvalidSession:
                logger.error(f"Invalid Query: {query}")

            sleep_ = randint(settings.DELAY_EACH_ACCOUNT[0], settings.DELAY_EACH_ACCOUNT[1])
            logger.info(f"Sleep {sleep_}s...")
            await asyncio.sleep(sleep_)

        sleep_ = randint(settings.SLEEP_TIME_BETWEEN_EACH_ROUND[0], settings.SLEEP_TIME_BETWEEN_EACH_ROUND[1])
        logger.info(f"<red>Sleep {sleep_}s...</red>")
        await asyncio.sleep(sleep_)
