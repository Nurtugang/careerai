import logging
import requests
from django.conf import settings
from datetime import datetime, timedelta
from .gemini_service import generate_search_queries, analyze_vacancies_batch

logger = logging.getLogger('core')


def get_hh_vacancies(student_profile=None, per_page=10, max_queries=1, batch_count=1):
    """
    Получает вакансии из HeadHunter API
    
    Args:
        student_profile: профиль студента (если авторизован)
        per_page: сколько вакансий вернуть
        max_queries: максимальное количество поисковых запросов (по умолчанию 1)
    """
    logger.info("=" * 80)
    logger.info("🌐 ЗАПРОС ВАКАНСИЙ ИЗ HeadHunter API")
    logger.info("=" * 80)
    
    list_url = settings.HH_API_URL
    headers = {'User-Agent': 'CareerAI/1.0'}

    all_vacancies = []
    unique_ids = set()
    
    # ==================== ГЕНЕРАЦИЯ ПОИСКОВЫХ ЗАПРОСОВ ====================
    if student_profile:
        logger.info(f"✅ Студент авторизован (ID: {student_profile.person_id})")
        logger.info(f"   Специальность: {student_profile.education.specialization if hasattr(student_profile, 'education') else 'Неизвестно'}")
        
        # Генерируем умные поисковые запросы через Gemini
        search_queries = generate_search_queries(student_profile, max_queries=max_queries)
        
        logger.info("-" * 80)
        logger.info(f"🔍 Будем искать по {len(search_queries)} {'запросу' if len(search_queries) == 1 else 'запросам'}:")
        for i, query in enumerate(search_queries, 1):
            logger.info(f"   {i}. '{query}'")
        
    else:
        logger.info("ℹ️  Гость (не авторизован)")
        search_queries = [None]  # Один запрос без фильтра
    
    # ==================== ПОИСК ПО ВСЕМ ЗАПРОСАМ ====================
    queries_used = 0
    min_vacancies_needed = 10  # Минимум вакансий для продолжения
    
    for idx, query in enumerate(search_queries, 1):
        logger.info("-" * 80)
        if query:
            logger.info(f"📡 Запрос #{idx}/{len(search_queries)}: '{query}'")
        else:
            logger.info(f"📡 Запрос #{idx}/{len(search_queries)}: без фильтра")
        
        params = {
            'area': '40',
            'per_page': 50,
            'page': 0,
            'order_by': 'publication_time'
        }
        
        if query:
            params['text'] = query
            params['experience'] = 'noExperience'
        
        try:
            response = requests.get(list_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            items = response.json().get('items', [])
            
            logger.info(f"   ✅ Получено вакансий: {len(items)}")
            
            new_count = 0
            for item in items:
                vacancy_id = item.get('id')
                if vacancy_id and vacancy_id not in unique_ids:
                    unique_ids.add(vacancy_id)
                    all_vacancies.append(item)
                    new_count += 1
            
            logger.info(f"   ✓ Добавлено новых уникальных: {new_count}")
            logger.info(f"   📊 Всего уникальных вакансий: {len(all_vacancies)}")
            
            queries_used += 1
            
            # ========== ПРОВЕРКА: НУЖЕН ЛИ ЕЩЕ ЗАПРОС? ==========
            if len(all_vacancies) < min_vacancies_needed and queries_used < len(search_queries):
                logger.warning(f"   ⚠️  Всего {len(all_vacancies)} вакансий (мин: {min_vacancies_needed})")
                logger.info(f"   ➡️  Автоматически делаем еще один поисковый запрос...")
                continue  # Идем к следующему запросу
            else:
                logger.info(f"   ✅ Достаточно вакансий, останавливаем поиск")
                break  # Хватит, останавливаемся
            
        except requests.RequestException as e:
            logger.error(f"   ❌ Ошибка запроса: {e}")
            queries_used += 1
            continue
    
    # ==================== ЗАГРУЗКА ДЕТАЛЕЙ ====================
    logger.info("-" * 80)
    logger.info(f"🔍 Загружаем детали для {len(all_vacancies)} вакансий...")
    
    vacancies = []
    for idx, item in enumerate(all_vacancies, 1):
        detail_url = item.get('url')
        if not detail_url:
            continue
        
        try:
            detail_response = requests.get(detail_url, headers=headers, timeout=5)
            detail_response.raise_for_status()
            item_details = detail_response.json()
            
            key_skills_list = [skill['name'] for skill in item_details.get('key_skills', [])]
            
            if idx <= 5:
                logger.info(f"  ✓ Вакансия #{idx}: {item.get('name', 'Без названия')}")
                logger.info(f"      Навыки: {', '.join(key_skills_list[:3]) if key_skills_list else 'не указаны'}")
        
        except requests.RequestException:
            key_skills_list = []
        
        # Форматируем зарплату
        salary = item.get('salary')
        salary_display = "Не указана"
        if salary:
            salary_from = salary.get('from')
            salary_to = salary.get('to')
            currency = salary.get('currency', '').upper()
            
            if salary_from and salary_to:
                salary_display = f"{salary_from:,} - {salary_to:,} {currency}".replace(',', ' ')
            elif salary_from:
                salary_display = f"от {salary_from:,} {currency}".replace(',', ' ')
            elif salary_to:
                salary_display = f"до {salary_to:,} {currency}".replace(',', ' ')
        
        vacancies.append({
            'id': item.get('id'),
            'title': item.get('name'),
            'company': item.get('employer', {}).get('name'),
            'city': item.get('area', {}).get('name'),
            'salary': salary_display,
            'url': item.get('alternate_url'),
            'employment': item.get('employment', {}).get('name', 'Не указано'),
            'snippet': item.get('snippet', {}).get('requirement') or "Нет описания.",
            'skills': key_skills_list,
        })
    
    if len(all_vacancies) > 5:
        logger.info(f"  ... и еще {len(all_vacancies) - 5} вакансий")
    
    logger.info(f"✅ Всего собрано вакансий: {len(vacancies)}")
    
    # ==================== GEMINI АНАЛИЗ ====================
    logger.info("-" * 80)
    if student_profile and vacancies:
        logger.info(f"🤖 Студент авторизован → запускаем Gemini-анализ...")
        
        # Анализируем через Gemini
        analyzed = analyze_vacancies_batch(vacancies, student_profile, batch_size=20, max_batches=batch_count)
        
        # Возвращаем топ-N (уже отсортированы внутри analyze_vacancies_batch)
        logger.info(f"✅ Возвращаем топ-{per_page} вакансий с Gemini-рекомендациями")
        logger.info("=" * 80)
        return analyzed[:per_page]
    else:
        logger.info(f"ℹ️  Гость → возвращаем первые {per_page} вакансий БЕЗ Gemini-анализа")
        logger.info("=" * 80)
        return vacancies[:per_page]