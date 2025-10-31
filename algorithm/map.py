from typing import Optional
import aiohttp
import asyncio
from logger import logger
OSRM_BASE = "https://router.project-osrm.org"
OSRM_PROFILE = "foot"

YANDEX_MAP_MODE = "pedestrian"

async def osrm_table(src_lat: float, src_lon: float,
                     destination_coords: list[tuple[float, float]]) -> Optional[list[list[float]]]:
    coords = [f"{src_lon},{src_lat}"] + [f"{lon},{lat}" for lat, lon in destination_coords]
    coords_str = ";".join(coords)
    print(coords)

    url = f"{OSRM_BASE}/table/v1/{OSRM_PROFILE}/{coords_str}"

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=50)) as session:
            async with session.get(url, params={"sources": "0"}) as r:
                r.raise_for_status()
                j = await r.json()

    durs = j.get("durations")
    if not durs or not durs[0]:
         logger.warning("OSRM Table не смог найти матрицу")
         return None
        #raise Exception("OSRM /table: пустой ответ durations")
    return durs


async def get_osrm_route(src_lat: float, src_lon: float,
                   dst_lat: float, dst_lon: float) -> tuple[float, float]:
    url = f"{OSRM_BASE}/route/v1/{OSRM_PROFILE}/{src_lon},{src_lat};{dst_lon},{dst_lat}"
    params = {"overview": "false"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                # обработка ответа
                route = data['routes'][0]
                return route['duration'], route['distance']
        except asyncio.TimeoutError:
            logger.warning("OSRM timeout")
            return None, None
        except Exception as e:
            logger.error(f"OSRM error: {e}")
            return None, None


def yandex_route_link(src_lat: float, src_lon:
                      float, dst_lat: float, dst_lon: float) -> str:
    return (
        f"https://yandex.ru/maps/?rtext="
        f"{src_lat:.6f}%2C{src_lon:.6f}~{dst_lat:.6f}%2C{dst_lon:.6f}"
        f"&rtt={YANDEX_MAP_MODE}"
    )
