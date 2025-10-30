import logging
import asyncio

from bot import bot, router, dp
from dataset import read_df, read_json

logging.basicConfig(level=logging.INFO)

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
