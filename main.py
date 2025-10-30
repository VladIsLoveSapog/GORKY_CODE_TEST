import token_parsing as token
from bot import bot,dp
import handlers.start
from logger import logger
import asyncio
from handlers import survey_router

dp.include_router(survey_router)
dp.include_router(handlers.start.router)

async def main():
    logger.info("Бот запущен")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception("Критическая ошибка в polling")


if __name__ == '__main__':
    asyncio.run(main())



