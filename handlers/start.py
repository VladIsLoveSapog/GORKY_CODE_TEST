from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states.survey import SurveyStates
from handlers.survey import CONTINUE
router = Router()

START_MESSAGE = """
Привет, я был разработан в рамках тествого задания для хакатона GORKYCODE2025 и 
я помогу тебе сформировать маршрут из достопримечательностей. Нажми кнопку 'Продолжить', если готов продолжить."
"""


@router.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Продолжить")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        START_MESSAGE,
        reply_markup=markup
    )
