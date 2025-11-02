# Shakarim Carrer AI
## О проекте
Третий AI-агент от [Shakarim University](https://aisana.shakarim.kz)
## Стек
- Python 3.10.11
- Django 5.2.7
- Tailwind CSS
## Инструкция
1. Клонируй репозиторий `git clone https://github.com/Nurtugang/careerai.git`
2. Создай и активируй виртуальную среду  `python -m venv venv & call venv/Scripts/activate`
2. Установи зависимости из req.txt `pip install -r req.txt`
3. Создай .env по примеру из .env.example `cp .env.example .env`
4. Сделай миграции `python manage.py migrate`
5. Собери статические файлы `python manage.py collectstatic`
6. Запусти локальный сервер `python manage.py runserver`