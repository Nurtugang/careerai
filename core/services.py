import logging
import requests
from django.conf import settings
from datetime import datetime, timedelta
from .ml_recommender import VacancyRecommender

logger = logging.getLogger('core')


def get_hh_vacancies(student_profile=None, per_page=10):
    logger.info("=" * 80)
    logger.info("🌐 ЗАПРОС ВАКАНСИЙ ИЗ HeadHunter API")
    logger.info("=" * 80)
    
    list_url = settings.HH_API_URL
    date_from = (datetime.now() - timedelta(days=30)).isoformat()

    fetch_count = 100 if student_profile else per_page
    
    logger.info(f"📋 Параметры запроса:")
    logger.info(f"  - Профиль студента: {'✓ Есть' if student_profile else '✗ Нет'}")
    logger.info(f"  - Запрашиваем вакансий: {fetch_count}")
    logger.info(f"  - Нужно вернуть: {per_page}")
    logger.info(f"  - Регион: Казахстан (area=40)")
    logger.info(f"  - Период: последние 30 дней (с {date_from[:10]})")

    params = {
        'area': '40',
        'publication_time_from': date_from,
        'per_page': fetch_count,
        'page': 0,
        'order_by': 'publication_time'
    }
    
    if student_profile:
        specialization = student_profile.education.specialization
        params['text'] = specialization
        params['experience'] = 'noExperience'
        logger.info(f"  - Фильтр по специальности: {specialization}")
        logger.info(f"  - Фильтр опыта: Без опыта")

    headers = {
        'User-Agent': 'CareerAI/1.0'
    }

    try:
        logger.info("-" * 80)
        logger.info(f"📡 Отправляем запрос к HeadHunter API...")
        logger.info(f"   URL: {list_url}")
        
        list_response = requests.get(list_url, params=params, headers=headers, timeout=10)
        list_response.raise_for_status()
        
        items = list_response.json().get('items', [])
        logger.info(f"✅ Получен ответ от HH API")
        logger.info(f"   HTTP Status: {list_response.status_code}")
        logger.info(f"   Вакансий в ответе: {len(items)}")
        
        if student_profile and len(items) < 10:
            logger.warning(f"⚠️  Мало вакансий ({len(items)}). Делаем запрос без фильтра по специальности...")
            
            params_fallback = {
                'area': '40',
                'publication_time_from': date_from,
                'per_page': 50,
                'page': 0,
                'experience': 'noExperience',
                'order_by': 'publication_time'
            }
            
            fallback_response = requests.get(list_url, params=params_fallback, headers=headers, timeout=10)
            fallback_response.raise_for_status()
            fallback_items = fallback_response.json().get('items', [])
            
            existing_ids = {item.get('id') for item in items}
            for fallback_item in fallback_items:
                if fallback_item.get('id') not in existing_ids:
                    items.append(fallback_item)
                    if len(items) >= 50:
                        break
            
            logger.info(f"  ✓ Добавлено вакансий: {len(items) - len(existing_ids)}")
        
        vacancies = []

        logger.info("-" * 80)
        logger.info(f"🔍 Загружаем детали вакансий (навыки, описание)...")
        
        for idx, item in enumerate(items, 1):
            detail_url = item.get('url')
            if not detail_url:
                logger.warning(f"  ⚠️  Вакансия #{idx}: URL отсутствует, пропускаем")
                continue

            try:
                detail_response = requests.get(detail_url, headers=headers, timeout=5)
                detail_response.raise_for_status()
                item_details = detail_response.json()
                
                key_skills_list = []
                for skill in item_details.get('key_skills', []):
                    key_skills_list.append(skill['name'])
                
                if idx <= 3:
                    logger.info(f"  ✓ Вакансия #{idx}: {item.get('name', 'Без названия')}")
                    logger.info(f"      Навыки: {', '.join(key_skills_list) if key_skills_list else 'не указаны'}")

            except requests.RequestException as e:
                logger.warning(f"  ⚠️  Вакансия #{idx}: Ошибка загрузки деталей - {e}")
                key_skills_list = []
            
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
        
        if len(items) > 3:
            logger.info(f"  ... и еще {len(items) - 3} вакансий загружено")
        
        logger.info(f"✅ Всего собрано вакансий: {len(vacancies)}")
        
        if student_profile and vacancies:
            logger.info("-" * 80)
            logger.info(f"🤖 Студент авторизован! Запускаем ML рекомендации...")
            logger.info(f"   Student ID: {student_profile.person_id}")
            logger.info(f"   Специальность: {student_profile.education.specialization if hasattr(student_profile, 'education') else 'Неизвестно'}")
            
            recommender = VacancyRecommender()
            vacancies = recommender.get_recommendations(
                student_profile=student_profile,
                vacancies=vacancies,
                top_n=per_page
            )
            logger.info(f"✅ ML рекомендации применены успешно")
        else:
            logger.info("-" * 80)
            if not student_profile:
                logger.info(f"ℹ️  Студент НЕ авторизован - возвращаем первые {per_page} вакансий БЕЗ рекомендаций")
            vacancies = vacancies[:per_page]
        
        logger.info("=" * 80)    
        return vacancies

    except requests.RequestException as e:
        logger.error("=" * 80)
        logger.error(f"❌ ОШИБКА при запросе к HH API")
        logger.error(f"   Тип: {type(e).__name__}")
        logger.error(f"   Сообщение: {str(e)}", exc_info=True)
        logger.error("=" * 80)
        return []