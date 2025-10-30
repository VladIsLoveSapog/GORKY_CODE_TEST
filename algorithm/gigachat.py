from gigachat import GigaChat
import token_parsing as token

GIGA_API_KEY = token.get_token("GIGA_API_KEY")

giga_lite =  GigaChat(
    credentials=GIGA_API_KEY,
    scope="GIGACHAT_API_PERS",
    model="GigaChat-2",
    verify_ssl_certs=False
)
# Пример: вернуть теги интересов в JSON
prompt = ('Пользователь: "граффити, панорамы и уютные кофейни". '
        'Выведи JSON-массив допустимых тегов: '
        '["стрит-арт","панорамы","кофейни","история","музеи","архитектура","парки","развлечения","религия"].\n[')
resp = giga_lite.chat(prompt)
print(resp)
print("[" + resp.choices[0].message.content.split("[",1)[-1])