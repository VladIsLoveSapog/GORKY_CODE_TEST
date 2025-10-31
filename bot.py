import math
import asyncio

from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters.command import Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext

from state import UserState
from map import *
from dataset import get_points
from giga import *

START_MESSAGE = """
Привет, я был разработан в рамках тествого задания для хакатона GORKYCODE2025.\n
Я помогу найти ближайшие достопримечательности на основе твоих интересов и проложу маршрут к ним.\n
Нажми кнопку 'Продолжить'.
"""

SEND_LOCATION_BTN = "📍 Отправить текущую локацию"
SEND_LOCATION_PLACEHOLDER = "Пришлите геопозицию…"

CONTINUE_BTN = "Продолжить"

RESET_BTN = "🔄 Сброс"

POINTS_NUMBER = 4

API_TOKEN = "YOUR_TOKEN"

MIN_WALK_SPEED = 2

# В сообщениях по умолчанию будет использоваться MARKDOWN разметка
bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)

dp = Dispatcher()
router = Router(name="main_router")

def get_user_coords(message: Message) -> tuple[float, float]:
    """
    Args:
        message: сообщение пользователя с координатами

    Returns:
        tuple(широта, долгота)
    """
    if not message.location:
        raise ValueError("В сообщении нет геолокации")

    loc = message.location

    lat = float(getattr(loc, "latitude", 0.0))
    lon = float(getattr(loc, "longitude", 0.0))

    return (lat, lon)


def get_top_points(durations:list[float]) -> list[int]:
    """
    Возвращает индексы топ POINTS_NUMBER ближайших точек
    Args:
        durations: секунды от начальной точки до каждой конечной

    Returns:
        Топ POINTS_NUMBER ближайших точек
    """
    pairs = [(i, d) for i, d in enumerate(durations) if d is not None]
    pairs_sorted = sorted(pairs, key=lambda t: t[1])
    return [i for i, _ in pairs_sorted[:POINTS_NUMBER]]

def calc_eta(distance_m: float, route_duration_sec: float):
    """
    Расчет ожидаемого времени в пути

    Args:
        distance_m: дистанция
        route_duration_sec: продолжительность пути в секундах

    Returns:
        Ожидаемое время в пути
    """
    eta_floor_min = (distance_m / MIN_WALK_SPEED) / 60.0
    eta_model_min = route_duration_sec / 60.0
    return math.ceil(max(eta_model_min, eta_floor_min))


def start_keyboard() -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=CONTINUE_BTN)],
            [KeyboardButton(text=RESET_BTN)],
        ],
        resize_keyboard=True
    )

def reset_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=RESET_BTN)]],
        resize_keyboard=True
    )

def location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить текущую локацию", request_location=True)],
            [KeyboardButton(text=RESET_BTN)]
        ],
        resize_keyboard=True,
        input_field_placeholder="Нажмите, чтобы отправить геопозицию"
    )



@router.message(UserState.waiting_for_interests)
async def handle_interests(message: Message, state: FSMContext):
    user_input = message.text.strip()

    # Извлечь category_ids (цифры)
    category_ids = await ask_category(user_input)

    if not category_ids:
        await message.answer("Не удалось распознать категории. Попробуйте переформулировать или нажмите 🔄 Сброс.")
        return

    # Сохраняем найденные категории
    await state.update_data(category_ids=category_ids)

    await message.answer(
        "Сколько у вас есть свободного времени в часах?",
        reply_markup=reset_keyboard()
    )
    await state.set_state(UserState.waiting_for_time)


@router.message(UserState.waiting_for_time)
async def handle_time_input(message: Message, state: FSMContext):
    """
    Обработка времени введенного пользователем
    """
    user_text = message.text.strip()

    time = await ask_time(user_text)

    if not time:
        await message.answer("Не удалось распознать количество часов. Попробуйте снова или нажмите 🔄 Сброс.")
        return

    hours = int(time.group())
    minutes = hours * 60

    await state.update_data(available_minutes=minutes)

    await message.answer(
        "📍 Теперь отправьте вашу текущую геолокацию, чтобы я нашёл ближайшие подходящие места.",
        reply_markup=location_keyboard()
    )

    await state.set_state(UserState.waiting_for_location)

async def ack_location(message: Message,
                       lat: float, lon: float) -> None:
    """
    Уведомляем пользователя, что информациях получена
    """
    await message.answer(
        "✅ Геолокация получена:\n"
        f"- Широта: *{lat:.6f}*\n"
        f"- Долгота: *{lon:.6f}*",
        disable_web_page_preview=True,
        reply_markup=reset_keyboard(),
    )

@dp.message(Command("start"))
async def start(message: Message, state: FSMContext) -> None:
    """
    Хэндлер на команду /start
    """
    await state.clear()
    await message.answer(
        START_MESSAGE,
        reply_markup=start_keyboard(),
    )

@dp.message(F.text == RESET_BTN)
@dp.message(Command("reset"))
async def reset_to_start(message: Message, state: FSMContext) -> None:
    """
    Обработчик кнопки «Сброс» и команды /reset — возвращаемся к стартовому экрану
    """
    await start(message, state)


@router.message(F.text == CONTINUE_BTN)
async def ask_interests(message: Message, state: FSMContext):
    """
    Спрашиваем что интересно пользователю
    """
    await state.set_state(UserState.waiting_for_interests)

    await message.answer(
        "Места какой направленности вы хотели бы посетить?",
        reply_markup=reset_keyboard()
    )


@router.message(F.location, UserState.waiting_for_location)
async def handle_location(message: Message, state: FSMContext):
    """
    Получение локации пользователя -> расчет матрицы расстояний -> получение ближайших -> получении информации о ближайших
    """
    user_lat = message.location.latitude
    user_lon = message.location.longitude

    await message.answer("📍 Геолокация получена. Ищу подходящие места…")

    data = await state.get_data()
    category_ids = data.get("category_ids", [])
    available_minutes = data.get("available_minutes", 0)

    # Получение информации о записях
    candidates = get_points(category_ids)
    destinations = list(zip(candidates.lat, candidates.lot))
    titles = candidates.title.tolist()
    descriptions = candidates.description.tolist()

    # OSRM: матрица расстояний
    durations_sec = await osrm_table(user_lat, user_lon, destinations)

    # Ближайшие записи
    top_idx = get_top_points(durations_sec)
    results = await asyncio.gather(*[
        get_osrm_route(user_lat, user_lon, destinations[i][0], destinations[i][1])
        for i in top_idx
    ])

    messages_count = 0

    for i, (duration_sec, distance_m) in zip(top_idx, results):
        minutes = calc_eta(distance_m, duration_sec)

        if minutes > available_minutes:
            continue  # долго идти — исключаем

        title = titles[i]
        raw_desc = descriptions[i]
        lat, lon = destinations[i]


        short_desc = await ask_point_description(title, raw_desc)
        link = yandex_route_link(user_lat, user_lon, lat, lon)

        messages_count += 1
        await message.answer(
            create_point_message(
                title,
                minutes,
                distance_m,
                short_desc,
                link
            ),
            disable_web_page_preview=True,
            reply_markup=start_keyboard()
        )

    if messages_count == 0:
        await message.answer("Не удалось найти места, до которых можно дойти за отведённое время.")

    await state.clear()

def create_point_message(title: str, minutes: int, distance_m: int, short_desc:str, link: str):
    return (
        f"*{title}*\n\n"
        f"⏱ Время в пути: *{minutes}* мин\n"
        f"📍 Расстояние: *{round(distance_m / 1000, 2)}* км\n\n"
        f"{short_desc}\n\n"
        f"Маршрут на [Яндекс.Картах]({link})"
    )
