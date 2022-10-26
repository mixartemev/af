import asyncio
import json
from httpcore import AsyncConnectionPool

from db import get_pairs

HOST = 'https://c2c.binance.com/'

HDRS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36',
    'Content-Type': 'application/json',
    'clienttype': 'web',
}

prs, pc, fts = asyncio.run(get_pairs())
pairs, pts, fiats = [{}, {}], {}, {}
for pt in pc:
    pts[pt['cur_id']] = pts.get(pt['cur_id'], []) + [pt['name']]
for pair in prs:
    tt = int(pair['sell'])
    pairs[tt][pair['cur_id']] = pairs[tt].get(pair['cur_id'], []) + [(pair['coin_id'], pair['id'])]
for fiat in fts:
    fiats[fiat['cur_id']] = fiats.get(fiat['cur_id'], []) + [(fiat['pt_id'], fiat['id'], fiat['need'], fiat['amount'])]


class Ad:
    def __init__(self, pid: int, adv: {}, tms: [], uid: int = None):
        self.id: int = int(adv['advNo']) - 10 ** 19
        self.pair_id: int = pid
        self.price: float = float(adv['price'])
        self.tms: (str,) = tuple(tm for tm in tms if tm in [a['identifier'] for a in adv['tradeMethods']])
        self.minFiat: float = float(adv['minSingleTransAmount'])
        self.maxFiat: float = float(adv['dynamicMaxSingleTransAmount'])
        self.user_id: int = uid


async def ads_all():
    ads, bd = {}, {"page": 1, "rows": 2}

    async def req(htp: AsyncConnectionPool, body: bytes, key: int):
        resp = await htp.request("POST", HOST+'bapi/c2c/v2/friendly/c2c/adv/search', headers=HDRS, content=body)
        if resp := json.loads(resp.content).get('data'):
            ads[key] = Ad(key, resp[0]['adv'], pts[resp[0]['adv']['fiatUnit']])

    async with AsyncConnectionPool(max_connections=28) as http:  # http2=True
        tasks = []
        for is_sell in 0, 1:
            bd.update({"tradeType": "SELL" if is_sell else "BUY"})
            for cur, coins in pairs[is_sell].items():
                bd.update({"fiat": cur, "payTypes": [f[0] for f in fiats[cur]] if is_sell else pts[cur]})
                pass
                for coin, pair_id in coins:
                    bd.update({"asset": coin})
                    tasks.append(req(http, json.dumps(bd).encode(), pair_id))
        await asyncio.gather(*tasks)
    return ads


res = asyncio.run(ads_all())
pass
