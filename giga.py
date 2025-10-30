from gigachat import GigaChat
import asyncio

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
