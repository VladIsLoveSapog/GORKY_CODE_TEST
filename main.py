import logging
import asyncio
import token_parsing as token
import handlers.start
import handlers.survey
from handlers.survey import *
from bot_instance import *
from algorithm.dataset import *
dp.include_router(handlers.start.router)
dp.include_router(handlers.survey.router)

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())