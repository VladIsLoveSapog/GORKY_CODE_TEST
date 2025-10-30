import math
import asyncio
import re
import pandas as pd

from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters.command import Command
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext

from state import UserState
from map import *
from dataset import read_df, read_json
from giga import ask_gigachat

START_MESSAGE = """
Привет, я был разработан в рамках тествого задания для хакатона GORKYCODE2025.\n
Я помогу найти ближайшие достопримечательности на основе твоих интересов и проложу маршрут к ним.\n
Нажми кнопку 'Продолжить'.
"""

SEND_LOCATION_MESSAGE = "📍 Отправить текущую локацию"
SEND_LOCATION_PLACEHOLDER = "Пришлите геопозицию…"

CONTINUE_BTN = "Продолжить"

RESET_BTN = "🔄 Сброс"

POINTS_NUMBER = 4


df = read_df()
category_tags = read_json()



def read_tg_token() -> str:
    with open("tg.cert", "r") as f:
        return f.readline().rstrip("\n")

# API_TOKEN = read_tg_token()
API_TOKEN = "YOUR_TOKEN"

MIN_WALK_SPEED = 2

# В сообщениях по умолчанию будет использоваться MARKDOWN разметка
bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
)

dp = Dispatcher()
router = Router(name="main_router")

DESTINATIONS = [
    (56.3290, 43.9980, "Точка 1"),
    (56.3269, 44.0059, "Точка 2"),
    (56.3155, 43.9994, "Точка 3"),
    (56.3245, 44.0101, "Точка 4"),
    (56.3322, 44.0150, "Точка 5"),
    (56.3188, 44.0302, "Точка 6"),
    (56.3370, 44.0050, "Точка 7"),
    (56.3415, 44.0120, "Точка 8"),
    (56.3200, 44.0000, "Точка 9"),
    (56.3100, 44.0200, "Точка 10"),
]


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


@router.message(UserState.waiting_for_interests)
async def handle_interests(message: Message, state: FSMContext):
    user_input = message.text.strip()

    # Сформировать промт на основе CATEGORY_TAGS
    prompt_parts = ["Вот категории и связанные с ними ключевые слова:"]
    for cat_id, tags in category_tags.items():
        prompt_parts.append(f"{cat_id} — {', '.join(tags)}")
    prompt_parts.append(f"\nПользователь написал: \"{user_input}\"")
    prompt_parts.append("Назови номера категорий, которые соответствуют интересам пользователя.")
    prompt = "\n".join(prompt_parts)

    await message.answer("🤖 Анализирую интересы...")

    model_response = await ask_gigachat(prompt)

    # Извлечь category_ids (цифры)
    category_ids = list(map(int, re.findall(r"\d+", model_response)))

    if not category_ids:
        await message.answer("Не удалось распознать категории. Попробуйте переформулировать или нажмите 🔄 Сброс.")
        return

    # Сохраняем найденные категории
    await state.update_data(category_ids=category_ids)

    await message.answer("Сколько у вас есть свободного времени в часах?", reply_markup=start_keyboard())
    await state.set_state(UserState.waiting_for_time)


@router.message(UserState.waiting_for_time)
async def handle_time_input(message: Message, state: FSMContext):
    user_text = message.text.strip()

    # Промт к GigaChat
    prompt = (
        f"Пользователь написал: \"{user_text}\".\n"
        "Определи, сколько часов указано. Верни только одно целое число без лишних слов."
    )

    await message.answer("Определяю доступное время...")

    response = await ask_gigachat(prompt)
    match = re.search(r"\d+", response)

    if not match:
        await message.answer("Не удалось распознать количество часов. Попробуйте снова или нажмите 🔄 Сброс.")
        return

    hours = int(match.group())
    minutes = hours * 60

    # Сохраняем в FSM
    await state.update_data(available_minutes=minutes)

    # Предлагаем отправить координаты
    location_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить текущую локацию", request_location=True)],
            [KeyboardButton(text=RESET_BTN)]
        ],
        resize_keyboard=True,
        input_field_placeholder="Нажмите, чтобы отправить геопозицию"
    )

    await message.answer(
        "📍 Теперь отправьте вашу текущую геолокацию, чтобы я нашёл ближайшие подходящие места.",
        reply_markup=location_kb
    )

    await state.set_state(UserState.waiting_for_location)


def keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SEND_LOCATION_MESSAGE, request_location=True)],
            [KeyboardButton(text=RESET_BTN)]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder=SEND_LOCATION_PLACEHOLDER,
    )


async def ack_location(message: Message,
                       lat: float, lon: float) -> None:
    await message.answer(
        "✅ Геолокация получена:\n"
        f"- Широта: *{lat:.6f}*\n"
        f"- Долгота: *{lon:.6f}*",
        disable_web_page_preview=True,
        reply_markup=keyboard(),
    )

# Хэндлер на команду /start
@dp.message(Command("start"))
async def start(message: Message, state: FSMContext) -> None:
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
    await start(message, start)


@router.message(F.text == CONTINUE_BTN)
async def ask_interests(message: Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_interests)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=RESET_BTN)]],
        resize_keyboard=True
    )

    await message.answer(
        "Места какой направленности вы хотели бы посетить?",
        reply_markup=kb
    )


@router.message(F.location, UserState.waiting_for_location)
async def handle_location(message: Message, state: FSMContext):
    user_lat = message.location.latitude
    user_lon = message.location.longitude

    await message.answer("📍 Геолокация получена. Ищу подходящие места…")

    data = await state.get_data()
    category_ids = data.get("category_ids", [])
    available_minutes = data.get("available_minutes", 0)

    # Фильтрация по категориям
    filtered_df = df[df["category_id"].isin(category_ids)]

    if filtered_df.empty:
        await message.answer("😕 Не нашлось подходящих мест для выбранных категорий.")
        return

    # 10 случайных записей
    candidates = filtered_df.sample(min(10, len(filtered_df)))
    destinations = list(zip(candidates.lat, candidates.lot))
    titles = candidates.title.tolist()
    descriptions = candidates.description.tolist()

    # OSRM: матрица расстояний
    durations_all = await osrm_table(user_lat, user_lon, destinations)
    durations_sec = durations_all[1:]

    # Топ-N ближайших
    top_idx = get_top_points(durations_sec)
    results = await asyncio.gather(*[
        get_osrm_route(user_lat, user_lon, destinations[i][0], destinations[i][1])
        for i in top_idx
    ])

    final_messages = []

    for i, (duration_sec, distance_m) in zip(top_idx, results):
        minutes = math.ceil(duration_sec / 60)

        if minutes > available_minutes:
            continue  # долго идти — исключаем

        title = titles[i]
        raw_desc = descriptions[i]
        lat, lon = destinations[i]
        link = yandex_route_link(user_lat, user_lon, lat, lon)

        # Промт для генерации краткого описания
        desc_prompt = (
            f"Название: {title}\n"
            f"Описание: {raw_desc}\n\n"
            f"Составь краткое описание (3-4 предложения) этого места для туриста."
        )

        short_desc = await ask_gigachat(desc_prompt)

        text = (
            f"*{title}*\n\n"
            f"⏱ Время в пути: *{minutes}* мин\n"
            f"📍 Расстояние: *{round(distance_m / 1000, 2)}* км\n\n"
            f"{short_desc}\n\n"
            f"[Маршрут на Яндекс.Картах]({link})"
        )

        final_messages.append(text)

    if not final_messages:
        await message.answer("🙁 Не удалось найти места, до которых можно дойти за отведённое время.")
    else:
        for msg in final_messages:
            await message.answer(msg, disable_web_page_preview=True, reply_markup=start_keyboard())

    await state.clear()
