import re
import pandas as pd

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

# Разбиваем coordinate на два отдельных столбца
df = pd.read_excel('cultural_objects_mnn.xlsx', engine="openpyxl")
df[["lat", "lot"]] = df["coordinate"].apply(parse_point).apply(pd.Series).astype("float64")

# избавляемся от coordinate из за ненадобности
df.drop(columns=["coordinate"], inplace=True)

category_map = {
 "1": {"история", "скульптура", "наука/техника"},
 "2": {"парки", "история", "развлечения"},
 "3": {"архитектура", "история", "музеи"},
 "4": {"набережная", "панорамы", "парки"},
 "5": {"архитектура", "история", "религия"},
 "7": {"музеи", "история", "архитектура"},
 "6": {"библиотека", "музеи", "театр"},
 "8": {"театр", "история", "развлечения"},
 "9": {"архитектура", "история", "необычно"},
 "10": {"история", "парки", "развлечения"},
}