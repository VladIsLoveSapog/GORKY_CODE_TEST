from typing import Tuple
from logger import logger
from algorithm.map import *
import math
import asyncio
from bot_instance import bot
import time, os

from algorithm.dataset import *
from algorithm.map import *
from algorithm.giga import *

async def construct_route(location : Tuple[str,str],available_minutes : int,category_ids : list[int]) -> Optional[str]:
    MIN_WALK_SPEED = 2
    POINTS_NUMBER = 4

    def get_top_points(durations:list[float]) -> list[int]:
        pairs = [(i, d) for i, d in enumerate(durations) if d is not None]
        pairs_sorted = sorted(pairs, key=lambda t: t[1])
        return [i for i, _ in pairs_sorted[:POINTS_NUMBER]]
    
    def calc_eta(distance_m: float, route_duration_sec: float):
        eta_floor_min = (distance_m / MIN_WALK_SPEED) / 60.0
        eta_model_min = route_duration_sec / 60.0
        return math.ceil(max(eta_model_min, eta_floor_min))
    
    def create_point_message(title: str, minutes: int, distance_m: int, short_desc:str, link: str):
        convert_distance = lambda x : round(x / 1000,2)
        return (
            f"*{title}*\n\n"
            f"Время в пути: {minutes} мин\n"
            f"Расстояние: {convert_distance(distance_m)} км\n\n"
            f"{short_desc}\n\n"
            f"Маршрут на [Яндекс.Картах]({link})"
        )

    candidates = get_points(category_ids)
    destinations = list(zip(candidates.lat, candidates.lot))
    titles = candidates.title.tolist()
    descriptions = candidates.description.tolist()

    (user_lat,user_lon) = location

    # OSRM: матрица расстояний
    dist_matrix = await osrm_table(user_lat, user_lon, destinations)

    # Ближайшие записи
    top_idx = get_top_points(dist_matrix)
    results = await asyncio.gather(*[
        get_osrm_route(user_lat, user_lon, destinations[i][0], destinations[i][1])
        for i in top_idx
    ])

    messages_count = 0
    messages = []
    for i, (duration_sec, distance_m) in zip(top_idx, results):
        minutes = calc_eta(distance_m, duration_sec)
        if minutes > available_minutes:
            continue

        title = titles[i]
        raw_desc = descriptions[i]
        lat, loc = destinations[i]
        short_desc = await ask_point_description(title, raw_desc)
        link = yandex_route_link(user_lat, user_lon, lat, loc)
        messages_count += 1
        
        answer = create_point_message(title,minutes,
            distance_m,short_desc,link)
        messages.append(answer)

    if messages_count == 0:
        return None
    
    logger.info(f"Сформирован ответ {messages}")
    return messages