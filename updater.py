import requests
import os
import sys
import time
import subprocess

def run_update(download_url, target_name):
    print("Начинаю загрузку обновления...")
    time.sleep(2)
    
    try:
        response = requests.get(download_url, stream=True)
        if response.status_code == 200:
            with open(target_name, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("Обновление завершено! Запускаю программу...")
            subprocess.Popen([target_name]) 
        else:
            print("Ошибка при скачивании.")
    except Exception as e:
        print(f"Ошибка: {e}")
    
    sys.exit()

if __name__ == "__main__":
    if len(sys.argv) > 2:
        run_update(sys.argv[1], sys.argv[2])