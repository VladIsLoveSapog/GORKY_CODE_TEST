import requests
from io import BytesIO
from staticmap import StaticMap, CircleMarker, Line

OSRM_BASE = "https://router.project-osrm.org"
OSRM_PROFILES = ("foot", "walking")

def osm_place_link(lat: float, lon: float, zoom: int = 16) -> str:
    # Ссылка на OpenStreetMap с маркером
    return f"https://www.openstreetmap.org/?mlat={lat:.6f}&mlon={lon:.6f}#map={zoom}/{lat:.6f}/{lon:.6f}"

def try_osrm_table_seconds(src_lat: float, src_lon: float, dsts_latlon: list[tuple[float, float]]):
    """
    Пробуем /table на нескольких профилях, возвращаем (profile, durations_sec[list]).
    durations_sec — время в секундах от src ко всем dsts.
    """
    coords = [f"{src_lon},{src_lat}"] + [f"{lon},{lat}" for lat, lon in dsts_latlon]
    coords_str = ";".join(coords)

    last_err = None
    for profile in OSRM_PROFILES:
        try:
            r = requests.get(
                f"{OSRM_BASE}/table/v1/{profile}/{coords_str}",
                params={"sources": "0"},
                timeout=10,
            )
            r.raise_for_status()
            j = r.json()
            durs = j.get("durations")
            if not durs or not durs[0]:
                raise RuntimeError("OSRM /table: пустой ответ durations")
            return profile, durs[0]
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"OSRM /table не удалось на профилях {OSRM_PROFILES}: {last_err}")

def try_osrm_route(profile: str, src_lat: float, src_lon: float, dst_lat: float, dst_lon: float, with_geometry: bool = True):
    """
    Возвращает (duration_sec, distance_m, path_latlon | None).
    Если with_geometry=True — добавляет список точек маршрута [(lat, lon), ...]
    """
    url = f"{OSRM_BASE}/route/v1/{profile}/{src_lon},{src_lat};{dst_lon},{dst_lat}"
    params = {"alternatives": "false"}
    if with_geometry:
        params.update({"overview": "full", "geometries": "geojson"})
    else:
        params.update({"overview": "false"})
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    route = data["routes"][0]
    duration = route["duration"]
    distance = route["distance"]
    if with_geometry:
        coords = route["geometry"]["coordinates"]  # [[lon, lat], ...]
        path_latlon = [(lat, lon) for lon, lat in coords]
    else:
        path_latlon = None
    return duration, distance, path_latlon


def render_route_png(path_latlon: list[tuple[float, float]], src: tuple[float, float], dst: tuple[float, float], width=900, height=600) -> BytesIO:
    """
    Рисует PNG: линия маршрута + маркеры старта/финиша. Возвращает BytesIO.
    Тайлы: OpenStreetMap (нужна атрибуция в подписи сообщения).
    """
    m = StaticMap(width, height, url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png")
    # линия (staticmap ждёт (lon, lat))
    line = Line([(lon, lat) for lat, lon in path_latlon], width=4, color='red')
    m.add_line(line)
    # маркеры
    m.add_marker(CircleMarker((src[1], src[0]), 'blue', 10))
    m.add_marker(CircleMarker((dst[1], dst[0]), 'red', 10))
    image = m.render()  # авто-зуум по добавленным слоям
    bio = BytesIO()
    image.save(bio, format="PNG")
    bio.seek(0)
    return bio


def yandex_place_link(lat: float, lon: float, zoom: int = 16) -> str:
    # Маркер точки
    return (
        f"https://yandex.ru/maps/?ll={lon:.6f}%2C{lat:.6f}"
        f"&z={zoom}&pt={lon:.6f},{lat:.6f},pm2rdl"
    )

def yandex_route_link(src_lat: float, src_lon: float, dst_lat: float, dst_lon: float, mode: str = "pedestrian") -> str:
    """
    mode: 'auto' (авто), 'pedestrian' (пешком), 'mt' (общественный транспорт)
    """
    return (
        f"https://yandex.ru/maps/?rtext="
        f"{src_lat:.6f}%2C{src_lon:.6f}~{dst_lat:.6f}%2C{dst_lon:.6f}"
        f"&rtt={mode}"
    )
