import token_parsing as token
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

TOKEN = token.get_token("BOT_TOKEN","./token.env")
if not TOKEN:
    print("Не удалось найти токен")
    exit(1)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)