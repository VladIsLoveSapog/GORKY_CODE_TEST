from typing import Tuple
from logger import logger
from algorithm.map import *
import math
import asyncio
from bot_instance import bot
import time, os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode, ContentType
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, FSInputFile
from aiogram import F

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

def keyboard() -> ReplyKeyboardMarkup:
    RESET_BTN = "Сброс"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить текущую локацию", request_location=True)],
            [KeyboardButton(text=RESET_BTN)]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Пришлите геопозицию…",
    )



async def create_new_route(location : Tuple[str,str], id : str):
    loc = location
    (lat,lon) = loc
    logger.info(f"Запускаем поиск пути для коориднат {lat} {lon}")
    user_link = yandex_place_link(lat, lon)
    await bot.send_message(
        text=(
            "✅ Геометка получена:\n"
            f"• Широта: <b>{lat:.6f}</b>\n"
            f"• Долгота: <b>{lon:.6f}</b>\n\n"
            f"Открыть в Яндекс.Картах: <a href=\"{user_link}\">ссылка</a>\n\n"
            "Считаю пешие ETA до 10 точек…"
        ),
        chat_id=id,
        disable_web_page_preview=True,
        #reply_markup=keyboard(),
    )

    # 3) Готовим вход для OSRM /table
    dsts_latlon = [(d[0], d[1]) for d in DESTINATIONS]  # [(lat, lon), ...]
    names = [d[2] for d in DESTINATIONS]

    # 4) Получаем оценки времени до всех точек и выбираем 3 ближайшие
    try:
        profile, durations_sec = try_osrm_table_seconds(lat, lon, dsts_latlon)
    except Exception as e:
        await bot.send_message(chat_id=id, text=f"Не удалось посчитать ETA через OSRM: {e}")
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
            logger.error(f"Не удалось выбрать точки для маршрута из точки {lat} {lon}")

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

        await bot.send_photo(chat_id=id, photo=FSInputFile(fname), caption=caption)
        try:
            os.remove(fname)
        except OSError:
            pass
    except Exception as e:
        await bot.send_message(f"Не удалось построить картинку маршрута: {e}")

    # 7) Отправляем список трёх ближайших
    profile_human = "пешком"
    text = (
            f"Три ближайшие цели ({profile_human}, OSRM):\n\n"
            + "\n".join(lines)
            + "\n\nИсточник маршрутизации: OSRM · Данные карты: © OpenStreetMap contributors"
    )
    await bot.send_message(chat_id = id,text=text, disable_web_page_preview=False)

