from asyncpg import create_pool, Record

dsn: str = 'postgres://artemiev:@/antifragility'


async def get_pairs() -> ([Record],):
    async with create_pool(dsn) as pool:
        pairs = await pool.fetch('SELECT id, coin_id, cur_id, sell FROM pair WHERE ex_id = 1')
        pts = await pool.fetch('SELECT name, cur_id FROM pt INNER JOIN pt_cur pc on name = pt_id WHERE rank >= 0 ORDER BY rank DESC')
        fiats = await pool.fetch('SELECT id, fiat.pt_id, cur_id, amount, target-amount as need FROM fiat INNER JOIN pt_cur pc on fiat.pt_id = pc.pt_id WHERE amount >= 0 ORDER BY need DESC')
    return pairs, pts, fiats
