import pandas as pd
from giga import *
import time
import os

# Настройка API ключа
client = OpenAI(api_key="your-openai-api-key")

def label_with_llm(text, prompt_template):
    """Функция для получения метки от LLM"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # или "gpt-4"
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides labels for text data."},
                {"role": "user", "content": f"{prompt_template}\n\nText: {text}"}
            ],
            max_tokens=100,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error processing text: {e}")
        return "Error"

def process_excel_file(input_file, output_file, text_column, prompt_template, delay=1):
    """
    Обрабатывает Excel файл и добавляет метки
    
    Args:
        input_file: путь к входному Excel файлу
        output_file: путь для сохранения результата
        text_column: название колонки с текстом для обработки
        prompt_template: промпт для LLM
        delay: задержка между запросами (в секундах)
    """
    
    # Чтение Excel файла
    df = pd.read_excel(input_file)
    
    # Проверка наличия колонки
    if text_column not in df.columns:
        print(f"Колонка '{text_column}' не найдена в файле")
        return
    
    # Добавляем колонку для меток
    df['label'] = ''
    
    # Обрабатываем каждую строку
    for index, row in df.iterrows():
        text = row[text_column]
        
        if pd.notna(text) and str(text).strip():
            print(f"Обработка строки {index + 1}/{len(df)}: {text[:50]}...")
            
            # Получаем метку от LLM
            label = label_with_llm(str(text), prompt_template)
            df.at[index, 'label'] = label
            
            # Задержка чтобы не превысить лимиты API
            time.sleep(delay)
        else:
            df.at[index, 'label'] = "Empty"
    
    # Сохраняем результат
    df.to_excel(output_file, index=False)
    print(f"Обработка завершена. Результат сохранен в {output_file}")

# Пример использования
if __name__ == "__main__":
    # Настройки
    INPUT_FILE = "input.xlsx"
    OUTPUT_FILE = "output_with_labels.xlsx"
    TEXT_COLUMN = "text"  # название колонки с текстом
    PROMPT_TEMPLATE = """
    Проанализируй следующий текст и определи его тональность (позитивный, негативный, нейтральный).
    Ответь только одним словом: "позитивный", "негативный" или "нейтральный".
    """
    
    process_excel_file(INPUT_FILE, OUTPUT_FILE, TEXT_COLUMN, PROMPT_TEMPLATE)