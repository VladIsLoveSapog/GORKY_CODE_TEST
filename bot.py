import logging
import math
import asyncio

from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode, ContentType
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, FSInputFile
from aiogram import F

from map import *

START_MESSAGE = """
Привет, я был разработан в рамках тествого задания для хакатона GORKYCODE2025.
я помогу найти ближайшие достопримечательности на основе твоих интересов и проложу маршрут к ним.
Нажми кнопку 'Продолжить'.
"""

SEND_LOCATION_MESSAGE = "📍 Отправить текущую локацию"
SEND_LOCATION_PLACEHOLDER = "Пришлите геопозицию…"

RESET_BTN = "🔄 Сброс"


POINTS_NUMBER = 4



# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

def read_tg_token() -> str:
    with open("tg.cert", "r") as f:
        return f.readline().rstrip("\n")

# API_TOKEN = read_tg_token()
API_TOKEN = "8344918974:AAFxzjCFQFckD_lp8RbDPy0-qABiS7_Sukk"

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
async def start(message: Message) -> None:
    await message.answer(
        START_MESSAGE,
        reply_markup=keyboard(),
    )


@dp.message(F.text == RESET_BTN)
@dp.message(Command("reset"))
async def reset_to_start(message: Message) -> None:
    """
    Обработчик кнопки «Сброс» и команды /reset — возвращаемся к стартовому экрану
    """
    await start(message)


# TODO: коммент
@router.message(F.content_type == ContentType.LOCATION)
@router.message(F.location)
async def handle_location(message: Message) -> None:
    """
    Получили точку → оценили все цели → показали топ-N с ETA и дистанцией.
    """
    src_lat, src_lon = get_user_coords(message)

    ack_location(message, src_lat, src_lon)

    # Готовим вход для OSRM /table
    destination_coords = [(d[0], d[1]) for d in DESTINATIONS]  # [(lat, lon), ...]
    titles = [d[2] for d in DESTINATIONS]

    # Получаем оценки времени до всех точек и выбираем POINTS_NUMBER ближайших
    durations_sec = osrm_table(src_lat, src_lon, destination_coords)[1:]
    top_idxes = get_top_points(durations_sec)

    # Для ближайших точек получаем детальные координаты и описание
    for i in top_idxes:
        dst_lat, dst_lon = destination_coords[i]
        name = titles[i]

        route_duration_sec, distance_m = try_osrm_route(src_lat, src_lon,
                                                        dst_lat, dst_lon)

        eta = calc_eta(distance_m, route_duration_sec)
        dist_km = round(float(distance_m) / 1000.0, 2)
        route_link = yandex_route_link(src_lat, src_lon,
                                       dst_lat, dst_lon)

        text = (
            f"*{name}*.\n\n"
            f"Примерное время в пути: *{eta}* мин."
            f"Дистанция: *{dist_km}* км пешком.\n\n"
            f"Маршрут на Яндекс Картах: {route_link}"
        )
        await message.answer(text, disable_web_page_preview=True, reply_markup=keyboard())


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
