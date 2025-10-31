import pandas as pd
import os
import sys
from pathlib import Path

def xlsx_to_csv_pandas(input_file, output_file=None, sheet_name=0):
    """
    Конвертирует XLSX файл в CSV используя pandas
    
    Args:
        input_file (str): Путь к входному XLSX файлу
        output_file (str, optional): Путь к выходному CSV файлу
        sheet_name (str/int): Название или индекс листа (по умолчанию первый лист)
    """
    try:
        # Если выходной файл не указан, создаем с тем же именем
        if output_file is None:
            output_file = Path(input_file).with_suffix('.csv')
        
        # Читаем XLSX файл
        df = pd.read_excel(input_file, sheet_name=sheet_name)
        df = df.drop('category_id', axis = 1)
        # Сохраняем в CSV
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        print(f"Успешно конвертирован: {input_file} -> {output_file}")
        
    except Exception as e:
        print(f"Ошибка при конвертации: {e}")

# Пример использования
if __name__ == "__main__":
    # Конвертация одного файла
    xlsx_to_csv_pandas("cultural_objects_mnn.xlsx", "cultural_objects_mnn.csv")
    
    # Или конвертация всех XLSX файлов в папке
    # for file in Path('.').glob('*.xlsx'):
    #     xlsx_to_csv_pandas(file)