from gigachat import GigaChat

GIGA_API_KEY = "MDE5YTMzYjItOGQ5OS03NDlkLWE5MzYtMDA0M2I2NjViYjMzOmQ0NTFlN2M3LTUwOTYtNGZkZS1iMmEzLTM5NDBjNWJjOWY1YQ==";

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
print("[" + resp.choices[0].message.content.split("[",1)[-1])  # мини-обрезка вывода
