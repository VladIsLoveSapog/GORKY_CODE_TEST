import token_parsing as token
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = token.get_token("BOT_TOKEN","./token.env")
if not TOKEN:
    print("Не удалось найти токен")
    exit(1)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)