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


async def construct_route(location: Tuple[str, str], available_minutes: int, category_ids: list[int]) -> Optional[str]:
    MIN_WALK_SPEED = 2
    POINTS_NUMBER = 5

    def get_top_points(durations: list[float]) -> list[int]:
        pairs = [(i, d) for i, d in enumerate(durations) if d is not None]
        pairs_sorted = sorted(pairs, key=lambda t: t[1])
        return [i for i, _ in pairs_sorted]

    def calc_eta(distance_m: float, route_duration_sec: float):
        eta_floor_min = (distance_m / MIN_WALK_SPEED) / 60.0
        eta_model_min = route_duration_sec / 60.0
        return math.ceil(max(eta_model_min, eta_floor_min))

    def create_point_message(title: str, minutes: int, distance_m: int, short_desc: str, link: str):
        convert_distance = lambda x: round(x / 1000, 2)
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

    (user_lat, user_lon) = location

    # OSRM: матрица расстояний
    table = await osrm_table(user_lat, user_lon, destinations)
    #print(table)

    def findDestinations(visited: list[int]) -> list[int]:
        #print(visited)
        last = visited[-1]
        cur_row = table[last]
        if len(visited) == len(cur_row):
            return visited
        row_wo_visited = [v for i, v in enumerate(cur_row) if i not in visited]
        visited.append(cur_row.index(min(row_wo_visited)))
        return findDestinations(visited)

    dist_matrix = table[0][1:]
    positions = [(user_lat, user_lon)]
    # Ближайшие записи
    top_idx = findDestinations([0])

    top_idx = [i-1 for i in top_idx][1:]
    print(top_idx)
        #get_top_points(dist_matrix)[:POINTS_NUMBER]
    positions += [(destinations[i][0], destinations[i][1]) for i in top_idx]
    positions = positions[:POINTS_NUMBER]
    results = await asyncio.gather(*[
        get_osrm_route(positions[i][0], positions[i][1], positions[i + 1][0], positions[i + 1][1])
        for i in range(len(positions) - 1)
    ])

    # positions = [(user_lat, user_lon)]
    # positions += [(destinations[i][0], destinations[i][1]) for i in top_idx]
    # for i in range(len(positions) - 1):
    #     results.append(
    #         get_osrm_route(positions[i][0], positions[i][1], positions[i + 1][0], positions[i + 1][1])
    #     )

    messages_count = 0
    messages = []
    last_lat = user_lat
    last_lon = user_lon
    total_time = 0
    for i, (duration_sec, distance_m) in zip(top_idx, results):
        minutes = calc_eta(distance_m, duration_sec)
        if minutes + total_time > available_minutes:
            # Не успеем дойти
            continue

        total_time += minutes
        if total_time > available_minutes:
            break

        title = titles[i]
        raw_desc = descriptions[i]
        lat, loc = destinations[i]
        short_desc = await ask_point_description(title, raw_desc)
        link = yandex_route_link(last_lat, last_lon, lat, loc)
        last_lat = lat
        last_lon = loc
        messages_count += 1

        answer = create_point_message(title, minutes,
                                      distance_m, short_desc, link)
        messages.append(answer)

    if messages_count == 0:
        return None

    logger.info(f"Сформирован ответ {messages}")
    return messages
