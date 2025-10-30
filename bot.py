import logging
import math
import asyncio

import time, os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode, ContentType
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, FSInputFile
from aiogram import F

from map import *

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

def read_tg_token() -> str:
    with open("tg.cert", "r") as f:
        return f.readline().rstrip("\n")

API_TOKEN = read_tg_token()

bot = Bot(token=API_TOKEN)
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

RESET_BTN = "🔄 Сброс"


# Хэндлер на команду /start
@dp.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(
        "Привет! Я принимаю геолокацию и проверяю её корректность.\n"
        "Нажми кнопку ниже или пришли локацию через скрепку.",
        reply_markup=keyboard(),
    )





def keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Отправить текущую локацию", request_location=True)],
            [KeyboardButton(text=RESET_BTN)]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Пришлите геопозицию…",
    )


# Обработчик кнопки «Сброс» и команды /reset — возвращаемся к стартовому экрану
@dp.message(F.text == RESET_BTN)
@dp.message(Command("reset"))
async def reset_to_start(message: Message) -> None:
    await start(message)


@router.message(F.content_type == ContentType.LOCATION)
@router.message(F.location)
async def handle_location(message: Message) -> None:
    import os, time, math
    from aiogram.types import FSInputFile

    # 1) Достаём координаты пользователя
    loc = message.location
    lat = float(getattr(loc, "latitude", 0.0))
    lon = float(getattr(loc, "longitude", 0.0))

    # 2) Сообщаем, что начали расчёт
    user_link = yandex_place_link(lat, lon)
    await message.answer(
        (
            "✅ Геометка получена:\n"
            f"• Широта: <b>{lat:.6f}</b>\n"
            f"• Долгота: <b>{lon:.6f}</b>\n\n"
            f"Открыть в Яндекс.Картах: <a href=\"{user_link}\">ссылка</a>\n\n"
            "Считаю пешие ETA до 10 точек…"
        ),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=keyboard(),
    )

    # 3) Готовим вход для OSRM /table
    dsts_latlon = [(d[0], d[1]) for d in DESTINATIONS]  # [(lat, lon), ...]
    names = [d[2] for d in DESTINATIONS]

    # 4) Получаем оценки времени до всех точек и выбираем 3 ближайшие
    try:
        profile, durations_sec = try_osrm_table_seconds(lat, lon, dsts_latlon)
    except Exception as e:
        await message.answer(f"Не удалось посчитать ETA через OSRM: {e}", reply_markup=keyboard())
        return

    idx_sorted = sorted(range(len(durations_sec)), key=lambda i: durations_sec[i])
    top3 = idx_sorted[:3]

    # 5) Для топ-3 забираем детальные данные маршрута (ETA/дистанция)
    lines = []
    for rank, i in enumerate(top3, start=1):
        dst_lat, dst_lon = dsts_latlon[i]
        try:
            dur_sec, dist_m, _ = try_osrm_route(profile, lat, lon, dst_lat, dst_lon, with_geometry=False)
        except Exception:
            dur_sec = durations_sec[i]
            dist_m = None

        MIN_WALK_SPEED = 1.9
        eta_floor = dist_m / MIN_WALK_SPEED / 60.0
        eta_min = math.ceil(max(dur_sec / 60.0, eta_floor))
        dist_km = (None if dist_m is None else round(float(dist_m) / 1000.0, 2))

        point_link = yandex_place_link(dst_lat, dst_lon)
        route_link = yandex_route_link(lat, lon, dst_lat, dst_lon, mode="pedestrian")

        if dist_km is None:
            line = (
                f"{rank}) {names[i]} — ~{eta_min} мин (пешком).\n"
                f"Точка: {point_link}\nМаршрут: {route_link}"
            )
        else:
            line = (
                f"{rank}) {names[i]} — ~{eta_min} мин, {dist_km} км (пешком).\n"
                f"Точка: {point_link}\nМаршрут: {route_link}"
            )
        lines.append(line)

    # 6) Строим маршрут к ближайшей цели, рендерим PNG и отправляем
    best_i = top3[0]
    best_dst_lat, best_dst_lon = dsts_latlon[best_i]
    try:
        dur_sec_best, dist_m_best, path_best = try_osrm_route(
            profile, lat, lon, best_dst_lat, best_dst_lon, with_geometry=True
        )
        png = render_route_png(path_best, (lat, lon), (best_dst_lat, best_dst_lon))
        fname = f"route_{int(time.time())}.png"
        with open(fname, "wb") as f:
            f.write(png.read())

        eta_min_best = math.ceil(float(dur_sec_best) / 60.0)
        dist_km_best = round(float(dist_m_best) / 1000.0, 2)

        caption = (
            f"Маршрут к ближайшей точке: {names[best_i]}\n"
            f"~{eta_min_best} мин, {dist_km_best} км (пешком)\n"
            f"Источник маршрутизации: OSRM · Карта: © OpenStreetMap contributors"
        )
        await message.answer_photo(photo=FSInputFile(fname), caption=caption, reply_markup=keyboard())
        try:
            os.remove(fname)
        except OSError:
            pass
    except Exception as e:
        await message.answer(f"Не удалось построить картинку маршрута: {e}", reply_markup=keyboard())

    # 7) Отправляем список трёх ближайших
    profile_human = "пешком"
    text = (
            f"Три ближайшие цели ({profile_human}, OSRM):\n\n"
            + "\n".join(lines)
            + "\n\nИсточник маршрутизации: OSRM · Данные карты: © OpenStreetMap contributors"
    )
    await message.answer(text, disable_web_page_preview=False, reply_markup=keyboard())


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
