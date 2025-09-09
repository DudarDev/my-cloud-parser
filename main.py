# main.py

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# URL страницы, которую мы будем открывать
URL = 'https://www.swappa.com/listings/apple-iphone-14'

def open_browser_with_profile():
    """
    Открывает браузер Chrome, используя сохраненный профиль,
    чтобы проходить проверку Cloudflare только один раз.
    """
    # Настраиваем опции Chrome
    chrome_options = Options()
    
    # САМОЕ ВАЖНОЕ: Указываем Selenium использовать папку 'chrome_profile'
    # для хранения данных сессии (cookies, кэш и т.д.).
    # При первом запуске эта папка будет создана.
    chrome_options.add_argument("--user-data-dir=chrome_profile")
    
    # Устанавливаем и запускаем драйвер Chrome
    # webdriver-manager автоматически скачает и настроит всё за нас
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    print(f"Открываю страницу: {URL}")
    driver.get(URL)

    print("-" * 30)
    print("Браузер открыт. Пожалуйста, пройди проверку Cloudflare (если она есть).")
    print("После того, как страница полностью загрузится, можешь закрыть это окно.")
    print("Скрипт будет ждать 60 секунд, прежде чем автоматически закроется.")
    print("-" * 30)

    # Даем тебе время, чтобы вручную пройти проверку
    time.sleep(60)

    # Закрываем браузер
    driver.quit()
    print("Браузер закрыт. Сессия сохранена в папке 'chrome_profile'.")


if __name__ == "__main__":
    open_browser_with_profile()