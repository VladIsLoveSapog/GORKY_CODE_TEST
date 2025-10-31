from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from states.survey import SurveyStates
from handlers.survey import CONTINUE
router = Router()

START_MESSAGE = """
Здравствуйте, я был разработан в рамках тествого задания для хакатона GORKYCODE2025 и 
я помогу вам сформировать маршрут из достопримечательностей. Нажмите кнопку 'Продолжить' или напишите какое нибудь сообщение, если готовы продолжить.
"""


@router.message(StateFilter("*"), Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Продолжить")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await state.clear()
    await message.answer(
        START_MESSAGE,
        reply_markup=markup
    )

