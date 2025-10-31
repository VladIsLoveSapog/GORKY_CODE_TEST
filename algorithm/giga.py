import asyncio
import re
from typing import Optional, Tuple
import token_parsing as token
from gigachat import GigaChat
from logger import logger
from algorithm.dataset import *


GIGA_API_KEY = token.get_token("GIGA_API_KEY","./token.env")

giga_lite =  GigaChat(
    credentials=GIGA_API_KEY,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-2",
    verify_ssl_certs=False
)


async def ask_gigachat(prompt: str) -> Tuple[str,bool]:
    try:
        response = await asyncio.to_thread(giga_lite.chat, prompt)
        logger.debug(f"Запрос {prompt} ответ {response}")
        return (response.choices[0].message.content.strip(),True)
    except Exception as e:
        logger.error(f"Не удалось совершить запрос с GigaChat из-за ошибки {e}")
        return (f"[Ошибка GigaChat: {e}]",False)

async def ask_category(input: str) -> list[int]:
    prompt_parts = ["Вот категории и связанные с ними ключевые слова:"]
    for cat_id, tags in category_tags.items():
        prompt_parts.append(f"{cat_id} — {', '.join(tags)}")
    prompt_parts.append(f"\nПользователь написал: \"{input}\"")
    prompt_parts.append("Назови номера категорий, которые соответствуют интересам пользователя. " \
        #Эту строчку я дописал
        "Ответ предоставь в виде набора цифр, например '1 2 3'. Не пиши лишних слов и не поясняй свой выбор.")
    prompt = "\n".join(prompt_parts)
    response, valid = await ask_gigachat(prompt)
    logger.info(f"Делаем запрос для поиска категорий {prompt} и получаем ответ {response}")
    if valid:
        return list(map(int, re.findall(r"\d+", response)))

    logger.warning(f"Не удалось сформировать категории из запроса {input}")
    return []


async def ask_time(input: str) -> str:
    #prompt = (
        #f"Пользователь написал: \"{input}\".\n"
        #"Определи, сколько часов указано. "
    #)
    prompt = (
    f"Пользователь написал: \"{input}\".\n\n"
    "Инструкции:\n"
    "1. Извлеки из фразы пользователя количество часов.\n"
    "2. Преобразуй это количество в число с плавающей точкой.\n"
    "   - 'один час' -> 1.0\n"
    "   - '2.5 ч' -> 2.5\n"
    "   - 'сорок пять минут' -> 0.75\n"
    "В ответе предоставь ТОЛЬКО число с плавающей точкой.\n"
)
    response, valid = await ask_gigachat(prompt)
    if not valid:
        logger.warning(f"Не удалось получить время из запроса {input}")
        return None
    logger.info(f"Делаем запрос с промптом {prompt} и получаем ответ {response}")
    #return re.search(r"\d+", response)
    return re.search(r"\d+\.?\d*", response)


async def ask_point_description(title: str, desc: str) -> str:
    desc_prompt = (
        f"Название: *{title}*\n"
        f"Описание: *{desc}*\n\n"
        f"Составь краткое описание (3-4 предложения) этого места для туриста."
    )
    response, valid = await ask_gigachat(desc_prompt)
    if not valid:
        logger.warning(f"Не удалось сформировать описание точек по запросу {desc_prompt}")
        return response
    
    logger.info(f"Делаем запрос с промптом {desc_prompt} и получаем ответ {response}")
    return response
