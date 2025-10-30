from dataclasses import dataclass
from typing import Optional, Tuple
from logger import logger
import asyncio
from bot_instance import bot

@dataclass
class UserAnswers:
    interests: Optional[str] = ""
    time_minutes: Optional[str] = ""
    location: Optional[Tuple[str,str]] = ""

active_requests : dict[str,UserAnswers] = {}

def add_request(userId : str,answers : dict[str,str]) -> Optional[str]:
    REQUEST_ALREADY_IN_PROCESS = "Похоже, мы уже обрабатываем ваш запрос. Пожалуйста, подождите завершения."
    if userId in active_requests:
        logger.info(f"Пользователь {userId} попытался добавить новый запрос, но его старый запрос еще не был обработан.")
        return REQUEST_ALREADY_IN_PROCESS
    
    logger.info(f"Пользователь {userId} попытался добавил новый запрос {answers}")
    serializedAnswers = UserAnswers(answers["interests"],answers["time"],answers["location"])
    active_requests[userId] = serializedAnswers

def fetch_next_request() -> Optional[ tuple[str,UserAnswers] ]:
    if active_requests:
        key = next(iter(active_requests))
        value = active_requests.pop(key)
        logger.info(f"Мы забрали запись с id {key} и значением {value} для обработки")
        return (key,value)
    else:
        return None

async def process_next_request() -> None:
    req = fetch_next_request()
    if req:
        await process_request(req)
    
async def process_request(record : tuple[str,UserAnswers]):
    id = record[0]
    answers = record[1]

    logger.info(f"Запрос пользователя с id {id} и значением {answers} обработывается.")
    #тут я полагаю будет обращение к ии
    from algorithm.route_construction import create_new_route
    await create_new_route(answers,id)
    logger.info(f"Запрос пользователя с id {id} и значением {answers} был обработан.")
    #result = "Здесь могла быть ваша ИИ"
    #await send_reply(id,result)
    #return result

async def send_reply(id : str,reply : str) -> None:
    try:
        await bot.send_message(chat_id=id,text=reply)
        logger.error(f"Результат {reply} отправлен пользователю с id {id}")
    except Exception as e:
        logger.error(f"Во время отправки сообщения {reply} пользователю с id {id} произошла ошибка {e}")
