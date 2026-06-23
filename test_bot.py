import asyncio
from telegram import Bot

async def test():
    bot = Bot("8526659236:AAHPuGIbaC3T_eNSg5FbUqKXmOpqwbr_bDA")
    me = await bot.get_me()
    print(me)

asyncio.run(test())
