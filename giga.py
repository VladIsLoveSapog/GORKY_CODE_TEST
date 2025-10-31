import asyncio
import re

from gigachat import GigaChat

from dataset import category_tags

GIGA_API_KEY = "YOUR_TOKEN";

giga_lite =  GigaChat(
    credentials=GIGA_API_KEY,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-2",
    verify_ssl_certs=False
)

async def ask_gigachat(prompt: str) -> str:
    try:
        response = await asyncio.to_thread(giga_lite.chat, prompt)
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Ошибка GigaChat: {e}]"

async def ask_category(input: str) -> list[int]:
    prompt_parts = ["Вот категории и связанные с ними ключевые слова:"]
    for cat_id, tags in category_tags.items():
        prompt_parts.append(f"{cat_id} — {', '.join(tags)}")
    prompt_parts.append(f"\nПользователь написал: \"{input}\"")
    prompt_parts.append("Назови номера категорий, которые соответствуют интересам пользователя.")
    prompt = "\n".join(prompt_parts)

    responce = await ask_gigachat(prompt)
    return  list(map(int, re.findall(r"\d+", responce)))


async def ask_time(input: str) -> str:
    prompt = (
        f"Пользователь написал: \"{input}\".\n"
        "Определи, сколько часов указано. Верни только одно целое число без лишних слов."
    )

    response = await ask_gigachat(prompt)
    return re.search(r"\d+", response)


async def ask_point_description(title: str, desc: str) -> str:
    desc_prompt = (
        f"Название: {title}\n"
        f"Описание: {desc}\n\n"
        f"Составь краткое описание (3-4 предложения) этого места для туриста."
    )

    return await ask_gigachat(desc_prompt)
