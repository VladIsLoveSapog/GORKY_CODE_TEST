# handlers/survey.py
from dataclasses import dataclass
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from states.survey import SurveyStates
from typing import Optional, Tuple
from logger import logger
from aiogram.enums import ParseMode, ContentType
from algorithm.giga import *
from aiogram.filters import StateFilter




ERROR_WRONG_REQUEST_MESSAGE = """
Ваше сообщение не было корректно обработано. Пожалуйста, следуйте инструкциям.
"""

CONTINUE = "Продолжить"

router = Router()

#Старт-опроса-----------------------------------------------------------------------------------------#
@router.message(StateFilter(None), F.text)
async def start_survey(message: Message, state: FSMContext):
    INTERESTS_QUESTION_MESSAGE = """
    Напиши, что вам интересно — например: стрит-арт, история, кофейни, панорамы и т.д.
    """

    await state.set_state(SurveyStates.interests)
    await message.answer(
        INTERESTS_QUESTION_MESSAGE,
        reply_markup=ReplyKeyboardRemove()
    )

#Интересы-----------------------------------------------------------------------------------------#
@router.message(SurveyStates.interests)
async def handle_interests(message: Message, state: FSMContext):
    TIME_QUESTION_MESSAGE = """
    Сколько у вас времени на прогулку? Ответ укажите в часах.
    """
    category_ids = await ask_category(message.text.strip())
    if not category_ids:
        await message.answer("Не удалось обработать ваш запрос. Попробуйте переформулировать или напишите /start.")
        return
    
    await state.update_data(interests=category_ids)
    logger.info(f"Пользователь {message.from_user.id} указал интересы: {message.text}, интерпретировано как {category_ids}")
    
    await state.set_state(SurveyStates.time)
    await message.answer(TIME_QUESTION_MESSAGE)

#Время-----------------------------------------------------------------------------------------#
@router.message(SurveyStates.time)
async def handle_time(message: Message, state: FSMContext):
    SEND_LOCATION_BUTTON_TEXT = """
    Отправить моё местоположение
    """

    ERROR_TIME_INPUT_QUESTION_MESSAGE = """
    По какой-то причине ваше сообщение не удалось обработать. Пожалуйста, переформулируйте его.
    """

    POSITION_QUESTION_MESSAGE = """
    Отправьте свою геопозицию — оттуда начнём маршрут!
    """

    async def validate_time(time : str) -> Optional[float]:
        hours_to_minutes = lambda x : x * 60.0
        response = await ask_time(user_text)
        try:
            hours = float(response.group())
            return hours_to_minutes(hours)
        except Exception:
            logger.info(f"Указанное пользователем {message.from_user.id} время {message.text} не удалось преобразовать во float")
            return None

    user_text = message.text.strip()
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} указал время: {message.text}")
    
    validated_time = await validate_time(user_text)
    if not validated_time:
        logger.info(f"Указанное пользователем {user_id} время {message.text} не прошло валидацию.")
        await message.answer(ERROR_TIME_INPUT_QUESTION_MESSAGE)
        return
    
    validated_time = int(validated_time)
    logger.info(f"Указанное пользователем {user_id} время {message.text} прошло валидацию и было интерпретировано как {validated_time} минут")
    await state.update_data(time=validated_time)
    await state.set_state(SurveyStates.location)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить текущую локацию", request_location=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Пришлите геопозицию",
    )

    await message.answer(POSITION_QUESTION_MESSAGE,reply_markup=keyboard)
    

#Местоположение-----------------------------------------------------------------------------------------#
@router.message(F.content_type == ContentType.LOCATION)
@router.message(F.location)
async def handle_location(message: Message, state: FSMContext):
    ERROR_NO_ROUTE_MESSAGE = """
    К сожалению нам не удалось построить маршрут. Пожалуйста, перезапустите бота с помощью /start переформулируйте ваши запросы.
    """
    user_id = message.from_user.id
    lat = message.location.latitude
    lon = message.location.longitude
    logger.info(f"Пользователь {user_id} ввел свое местоположение: широта {lat} долгота {lon}.")   

    data = await state.get_data()
    await message.answer(
        f"Спасибо за то что воспользовались нашим ботом!\n"
        f"Пожалуйста, подождите немного, пока мы обработаем ваш запрос.",
        reply_markup=ReplyKeyboardRemove()
    )

    from algorithm.route_construction import construct_route
    routes_messages = await construct_route((lat,lon),data["time"],data["interests"])
    logger.info(f"Сформирован маршрут {routes_messages}")
    await state.clear()
    if not routes_messages:
        await message.answer(ERROR_NO_ROUTE_MESSAGE)
    else:
        for msg in routes_messages:
            logger.debug(f"Отвечаем {msg}")
            await message.answer(msg)
#--------------------------------------------------------------------------------------------------#