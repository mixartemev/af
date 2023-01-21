import asyncio
import json
from asyncio import run

from httpcore import AsyncConnectionPool

from cycle import HOST, HDRS


def hsp(ct: str):
    return {
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            [b'content-type', ct.encode()],
        ]
    }


def bsp(b: str = '', mb: bool = False):
    return {
        'type': 'http.response.body',
        'body': b.encode(),
        'more_body': mb
    }


async def app(scope, receive, send):
    if scope['path'] == '/sse':
        await send(hsp('text/event-stream'))
        for n in range(30):
            await send(bsp(str(n), True))
            await asyncio.sleep(1)
        await send(bsp())
    elif scope['path'] == '/usr':
        await send(hsp('application/json'))
        await send(bsp(json.dumps({'user': 42})))
    else:
        await send({
            'type': 'http.response.start',
            'status': 404,
        })
        await send(bsp())


async def rrr():
    async with AsyncConnectionPool() as http:
        body = b'{"page": 1, "rows": 2, "tradeType": "BUY", "fiat": "USD", "payTypes": ["DenizBank", "TinkoffNew", "Produbanco", "BancoBolivariano", "BancoDelPacifico", "BancoGuayaquil", "BankArgentina", "AirTM", "BACcostarica", "BankTransferCosta", "BankTransferCosta", "Cashapp", "BanescoPanama", "PerfectMoney", "Wise", "Banesco", "Pix", "Revolut", "ZEN", "BancoDeCostaRica", "Zelle", "SantanderArgentina", "BankofAmerica", "MoneyGram", "BACCredomatic", "BCRBank", "BankofGeorgia", "NETELLER", "SkrillMoneybookers", "BANK", "BancoBrubankNew", "Reba", "BancoDelSol", "BancoGeneralPanama", "Nequi", "BanistmoPanama", "SpecificBank", "BAKAIBANK", "Paysera", "ScotiabankCostaRica", "Paytm", "BankIndia", "UPI", "StandardChartered", "Venmo", "MPesaKenya", "CashDeposit", "MeezanBank", "AlliedBankLimited", "Raast", "EasypaisaPK", "JazzCash", "Upaisa", "MoMoNew", "StanbicBank", "SadaPay", "Payall", "AccessBank", "IMPS", "WesternUnion", "WorldRemit", "MTNMobileMoney", "MpesaVodaphone", "MpesaPaybill", "Uphold", "TigoPesa", "airtelmoney", "CreditEuropeBank", "CitibankRussia", "ABA", "BandesUruguay", "BankRepublicUruguay", "CentralBankofUruguay", "RedPagos", "OcaBlue", "Interbank", "BancoDeCredito", "CreditBankofPeru", "ItauUruguay", "MercadoPagoNew", "Prex", "LemonCash", "Garanti", "KuveytTurk", "QNB", "BancolombiaSA", "BancoBACCredomaticSV", "PrivatBank", "Bakong", "ACLEDA", "KHQR", "PiPay", "NaranjaX", "PhonePe", "GPay", "Uzcard", "Humo", "Apelsin", "Kapitalbank", "Zinli", "MercantilBankPanama", "Mony", "BancoPichincha"], "asset": "DOGE"}'
        resp = await http.request("POST", HOST+'bapi/c2c/v2/friendly/c2c/adv/search', headers=HDRS, content=body)
        print(json.loads(resp.content).get('data'))

run(rrr())
