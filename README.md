## Требования

**Python 3.7+**

**aiohttp**

**MongoDB**

## Установка

```bash
pip install -r requirements.txt
```
##

Конфигурация БД, сервера, и API_KEY для использования Google Drive Api хранятся в `config/config.yaml`
Сейчас там хранится API_KEY специально созданного под это дело проекта. При необходимости создать новый.




## Запуск
```bash
python main.py
```
##
В браузере:

    http://localhost:5000/

Главная страница незарегистрированного пользователя:

    http://localhost:5000/public_homepage
    
 Регистрация:
 
    http://localhost:5000/register
  
 Страница входа:
 
    http://localhost:5000/login
    
  Сохраняются ссылки в формате
  
    https://drive.google.com/open?id=ExAmplEiD__12345
  
  ##
  * При нажатии кнопки "Remove User" пользователь удаляется мгновенно.
  * При нажатия кнопки "Download",все файлы скачаются .zip архивом. Есть задержка после нажатия т.к. делается пауза между 
  запросами к api.
    


