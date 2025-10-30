import re
import html
import json

import pandas as pd

XLS_TAG_RE = re.compile(r"<[^>]+>")

XLSX_PATH = "cultural_objects_mnn.xlsx"
JSON_PATH = "category_id_to_tags.json"

def clean_html(text: object) -> object:
    """Очистка текста pandas от html"""
    if pd.isna(text):
        return text

    s = str(text)
    s = html.unescape(s)
    s = XLS_TAG_RE.sub(" ", s)
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    return s.strip()

def parse_point(s: str):
    """
    Преобрзование столбца coordinate: POINT (lot lat)
    В отдельные столбцы lat и lot

    lat - широта
    lot - долгота
    """
    if pd.isna(s):
        return (None, None)
    s = str(s).strip()
    m = re.search(r"POINT\s*\(\s*([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*\)", s, flags=re.I)
    return (float(m.group(2)), float(m.group(1)))


def read_df(path: str = XLSX_PATH) -> pd.DataFrame:
    # Чтение датасета
    df = pd.read_excel(path, engine="openpyxl")

    # Очистка колонок от html
    df['description'] = df['description'].map(clean_html)
    df['title'] = df['title'].map(clean_html)

    # Разбиваем coordinate на два отдельных столбца
    df[["lat", "lot"]] = df["coordinate"].apply(parse_point).apply(pd.Series).astype("float64")

    # избавляемся от coordinate из за ненадобности
    df.drop(columns=["coordinate"], inplace=True)

    return df


def read_json(path: str = JSON_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
