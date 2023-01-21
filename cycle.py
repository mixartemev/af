import json
import logging
from asyncio import gather, run
from asyncpg import create_pool, Record
from httpcore import AsyncConnectionPool

logging.basicConfig(level=logging.DEBUG)

DSN: str = 'postgres://artemiev:@/antifragility'
HOST: str = 'https://c2c.binance.com/'
ADS_PTH: str = 'bapi/c2c/v2/friendly/c2c/adv/search'
HDRS: {str: str} = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36',
    'Content-Type': 'application/json',
    'clienttype': 'web',
}


async def cycle() -> ([Record],):
    async with create_pool(DSN) as pool:
        # get initial data from db
        pairs_flat = await pool.fetch('SELECT id, coin_id, cur_id, sell FROM pair')  # WHERE ex_id = 1
        pts_flat = await pool.fetch('SELECT name, cur_id FROM pt INNER JOIN ptc pc on name = pt_id WHERE rank >= 0 ORDER BY rank DESC')
        fiats_flat = await pool.fetch('SELECT fiat.id, pt_id, cur_id, amount, target-amount as need FROM fiat INNER JOIN ptc on fiat.ptc_id = ptc.id WHERE amount >= 0 and NOT blocked ORDER BY need DESC')
        # users_flat = await pool.fetch('SELECT fiat.id, pt_id, cur_id, amount, target-amount as need FROM fiat INNER JOIN ptc on fiat.ptc_id = ptc.id WHERE amount >= 0 and NOT blocked ORDER BY need DESC')

        # data transform
        pairs, pts, fiats = [{}, {}], {}, {}
        for pt in pts_flat:
            pts[pt['cur_id']] = pts.get(pt['cur_id'], []) + [pt['name']]
        for pair in pairs_flat:
            tt = int(pair['sell'])
            pairs[tt][pair['cur_id']] = pairs[tt].get(pair['cur_id'], []) + [(pair['coin_id'], pair['id'])]
        for fiat in fiats_flat:
            fiats[fiat['cur_id']] = fiats.get(fiat['cur_id'], []) + [(fiat['pt_id'], fiat['id'], fiat['need'], fiat['amount'])]

        # data containers
        new_ads, tasks, bd = {}, [], {"page": 1, "rows": 2}

        # func for async task
        async def req(htp: AsyncConnectionPool, body: {}, pid: int):
            resp = await htp.request("POST", HOST+ADS_PTH, headers=HDRS, content=json.dumps(body).encode())
            if res := json.loads(resp.content).get('data'):
                new_ads[pid] = Ad(pid, res[0]['adv'], pts[res[0]['adv']['fiatUnit']])
                print(pid, end='.')
            else:
                print(f'\nNO [{pid}] Ads for {body.pop("payTypes")}:(')
                resp = await htp.request("POST", HOST+ADS_PTH, headers=HDRS, content=json.dumps(body).encode())
                if res := json.loads(resp.content).get('data'):
                    print(f'Only for', res)

        # async getting ads from c2c.binance.com
        async with AsyncConnectionPool(max_connections=2) as http:  # http2=True
            for is_sell in 0, 1:
                bd.update({"tradeType": "SELL" if is_sell else "BUY"})
                for cur, coins in pairs[is_sell].items():
                    bd.update({"fiat": cur, "payTypes": [f[0] for f in fiats[cur]] if is_sell else pts[cur]})
                    for coin, pair_id in coins:
                        bd.update({"asset": coin})
                        tasks.append(req(http, bd, pair_id))
            await gather(*tasks)

        # stat results
        inc = len(new_ads)
        olc = len(pairs_flat)
        print(f'\n{inc}/{olc} ads received.')
        if inc < olc:
            print(olc-inc, 'pairs missed:', str(set(range(1, olc+1))-set(new_ads.keys())))

        # transform input data from c2c.binance to sql insert list of tuples
        insert_data = [(new_ad.id, new_ad.pair_id, new_ad.price, new_ad.minFiat, new_ad.maxFiat, 0) for new_ad in new_ads.values()]
        # sql execute
        upd_sql: str = '''
        INSERT INTO ad (id, pair_id, price, "minFiat", "maxFiat", status)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (id) DO UPDATE 
        SET price = excluded.price, "maxFiat" = excluded."maxFiat", updated_at = now();'''
        await pool.executemany(upd_sql, insert_data)


class Ad:  # class helps to create ad object from input data
    def __init__(self, pid: int, adv: {}, tms: [], uid: int = None):
        self.id: int = int(adv['advNo']) - 10 ** 19
        self.pair_id: int = pid
        self.price: float = float(adv['price'])
        self.tms: (str,) = tuple(tm for tm in tms if tm in [a['identifier'] for a in adv['tradeMethods']])
        self.minFiat: float = float(adv['minSingleTransAmount'])
        self.maxFiat: float = float(adv['dynamicMaxSingleTransAmount'])
        self.user_id: int = uid


if __name__ == '__main__':
    run(cycle())
