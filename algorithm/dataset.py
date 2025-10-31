import re
import html
import json

import pandas as pd

XLS_TAG_RE = re.compile(r"<[^>]+>")

XLSX_PATH = "./data/cultural_objects_mnn.xlsx"
JSON_PATH = "./data/category_id_to_tags.json"

RECORDS_NUMBER = 12


def clean_html(text: object) -> object:
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
    if pd.isna(s):
        return (None, None)
    s = str(s).strip()
    m = re.search(r"POINT\s*\(\s*([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*\)", s, flags=re.I)
    return (float(m.group(2)), float(m.group(1)))


def read_df(path: str = XLSX_PATH) -> pd.DataFrame:
    df = pd.read_excel(path, engine="openpyxl")
    df['description'] = df['description'].map(clean_html)
    df['title'] = df['title'].map(clean_html)
    df[["lat", "lot"]] = df["coordinate"].apply(parse_point).apply(pd.Series).astype("float64")
    df.drop(columns=["coordinate"], inplace=True)
    return df


def read_json(path: str = JSON_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
category_tags = read_json()


def get_points(category_ids: list[str]) -> pd.DataFrame:
    df = read_df()
    filtered_df = df[df["category_id"].isin(category_ids)]

    return filtered_df.sample(min(RECORDS_NUMBER, len(filtered_df)))


