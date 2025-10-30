import requests
import aiohttp

OSRM_BASE = "https://router.project-osrm.org"
OSRM_PROFILE = "foot"

YANDEX_MAP_MODE = "pedestrian"

async def osrm_table(src_lat: float, src_lon: float,
               destination_coords: list[tuple[float, float]]) -> list[float]:
    """
    osrm/table для профиля OSRM_PROFILE, строит матрицу расстояний от начальной точки ко всем конечным точкам.

    Args:
        src_lat: Широта начальной точки в градусах.
        src_lon: Долгота начальной точки в градусах.
        destination_coords: Список точек (lat, lon).

    Returns:
        Список с секундами пути от исходной точки до каждой конечной
    """
    coords = [f"{src_lon},{src_lat}"] + [f"{lon},{lat}" for lat, lon in destination_coords]
    coords_str = ";".join(coords)

    url = f"{OSRM_BASE}/table/v1/{OSRM_PROFILE}/{coords_str}"

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            async with session.get(url, params={"sources": "0"}) as r:
                r.raise_for_status()
                j = await r.json()

    durs = j.get("durations")
    if not durs or not durs[0]:
        raise Exception("OSRM /table: пустой ответ durations")
    return durs[0]


async def get_osrm_route(src_lat: float, src_lon: float,
                   dst_lat: float, dst_lon: float) -> tuple[float, float]:
    """
    osrm/route для профиля OSRM_PROFILE, строит маршрут от точки до точки с вычислением времени и расстояния

    Args:
        src_lat: Широта начальной точки в градусах.
        src_lon: Долгота начальной точки в градусах.
        dst_lat: Широта точки назначения в градусах.
        dst_lon: Долгота точки назначения в градусах.

    Returns:
        tuple(секунды, метры)
    """
    url = f"{OSRM_BASE}/route/v1/{OSRM_PROFILE}/{src_lon},{src_lat};{dst_lon},{dst_lat}"
    params = {"overview": "false"}

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        async with session.get(url, params=params) as r:
            r.raise_for_status()
            data = await r.json()

    route = data["routes"][0]

    duration: float = route["duration"]
    distance: float = route["distance"]
    return duration, distance


def yandex_route_link(src_lat: float, src_lon:
                      float, dst_lat: float, dst_lon: float) -> str:
    """
    Формирует ссылку на построение маршрута Яндекс карт

    Args:
        src_lat: Широта начальной точки в градусах.
        src_lon: Долгота начальной точки в градусах.
        dst_lat: Широта точки назначения в градусах.
        dst_lon: Долгота точки назначения в градусах.

    Returns:
        URL яндекс карт с маршрутом
    """
    return (
        f"https://yandex.ru/maps/?rtext="
        f"{src_lat:.6f}%2C{src_lon:.6f}~{dst_lat:.6f}%2C{dst_lon:.6f}"
        f"&rtt={YANDEX_MAP_MODE}"
    )
