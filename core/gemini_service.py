import logging
import json
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger('core')

# Инициализация Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-lite')


def generate_search_queries(student_profile, max_queries=1):
    """
    Генерирует поисковые запросы для HH API на основе профиля студента
    
    Args:
        student_profile: объект StudentProfile
        max_queries: максимальное количество запросов (по умолчанию 1)
        
    Returns:
        list: список поисковых запросов (строки)
    """
    logger.info("=" * 80)
    logger.info("🤖 ГЕНЕРАЦИЯ ПОИСКОВЫХ ЗАПРОСОВ ЧЕРЕЗ GEMINI")
    logger.info("=" * 80)
    
    try:
        # Собираем данные студента
        specialization = student_profile.education.specialization if hasattr(student_profile, 'education') else "Неизвестно"
        course = student_profile.course_number or "Неизвестно"
        gpa = float(student_profile.gpa) if student_profile.gpa else 0.0
        
        # Топ-10 предметов с хорошими оценками
        top_subjects = student_profile.academic_records.filter(
            grade__in=['A', 'A-', 'B+', 'B']
        ).order_by('-score')[:10]
        
        subjects_list = [record.subject_name for record in top_subjects]
        
        # Практики
        practices = student_profile.practices.all()[:3]
        practices_list = [p.practice_type for p in practices if p.practice_type]
        
        logger.info(f"📚 Данные студента:")
        logger.info(f"   - Специальность: {specialization}")
        logger.info(f"   - Курс: {course}")
        logger.info(f"   - GPA: {gpa}")
        logger.info(f"   - Топ предметов: {len(subjects_list)}")
        logger.info(f"   - Практики: {len(practices_list)}")
        logger.info(f"   - Макс. запросов: {max_queries}")
        
        # Формируем промпт для Gemini
        prompt = f"""
Ты — эксперт по карьерному консультированию и подбору вакансий в Казахстане.

ПРОФИЛЬ СТУДЕНТА:
- Специальность: {specialization}
- Курс обучения: {course}
- Средний балл (GPA): {gpa}
- Сильные предметы: {', '.join(subjects_list[:5]) if subjects_list else 'Нет данных'}
- Опыт практик: {', '.join(practices_list) if practices_list else 'Нет опыта'}

ЗАДАЧА:
Сгенерируй {max_queries} {'поисковый запрос' if max_queries == 1 else 'поисковых запроса'} для сайта HeadHunter (hh.kz), {'который поможет' if max_queries == 1 else 'которые помогут'} найти подходящие вакансии для этого студента.

ТРЕБОВАНИЯ:
1. Запросы должны быть НА РУССКОМ языке
2. {'Выбери САМЫЙ релевантный запрос' if max_queries == 1 else 'Включи синонимы и смежные специальности'}
3. Учитывай уровень: "без опыта", "стажер", "junior", "начинающий"
4. Запросы должны быть короткими (2-4 слова)
5. {'Запрос должен максимально точно отражать специальность' if max_queries == 1 else 'Разнообразь запросы (не только точное название специальности)'}

ФОРМАТ ОТВЕТА:
Верни ТОЛЬКО JSON массив строк, без markdown, без пояснений:
{f'["запрос 1"]' if max_queries == 1 else '["запрос 1", "запрос 2", ...]'}

ПРИМЕР для специальности "Программная инженерия" (max_queries={max_queries}):
{f'["junior python разработчик"]' if max_queries == 1 else '["junior python разработчик", " программист", "начинающий backend"]'}
"""
        
        logger.info("-" * 80)
        logger.info("📤 Отправляем запрос к Gemini...")
        
        # Отправляем запрос
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        logger.info("✅ Ответ получен от Gemini")
        logger.info(f"📥 Сырой ответ:\n{response_text}")
        
        # Парсим JSON
        # Убираем возможные markdown-обертки
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        queries = json.loads(response_text)
        
        if not isinstance(queries, list):
            raise ValueError("Ответ не является массивом")
        
        # Валидация
        queries = [q.strip() for q in queries if isinstance(q, str) and len(q.strip()) > 0]
        
        # Ограничиваем до max_queries
        queries = queries[:max_queries]
        
        if len(queries) < 1:
            raise ValueError(f"Слишком мало запросов: {len(queries)}")
        
        logger.info("-" * 80)
        logger.info(f"✅ Успешно сгенерировано запросов: {len(queries)}")
        for i, query in enumerate(queries, 1):
            logger.info(f"   {i}. {query}")
        logger.info("=" * 80)
        
        return queries
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Ошибка парсинга JSON: {e}")
        logger.error(f"   Ответ Gemini: {response_text}")
        # Fallback: возвращаем базовый запрос
        return [specialization] if specialization != "Неизвестно" else ["стажер без опыта"]
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ ОШИБКА ПРИ ГЕНЕРАЦИИ ЗАПРОСОВ")
        logger.error(f"   Тип: {type(e).__name__}")
        logger.error(f"   Сообщение: {str(e)}", exc_info=True)
        logger.error("=" * 80)
        # Fallback
        return [specialization] if specialization != "Неизвестно" else ["стажер без опыта"]
    

def analyze_vacancies_batch(vacancies, student_profile, batch_size=20, max_batches=1):
    """
    Анализирует список вакансий через Gemini (группами по batch_size)
    
    Args:
        vacancies: список словарей с вакансиями
        student_profile: объект StudentProfile
        batch_size: сколько вакансий анализировать за раз (по умолчанию 20)
        
    Returns:
        list: вакансии с добавленными gemini_score и reasoning
    """
    logger.info("=" * 80)
    logger.info(f"🤖 BATCH-АНАЛИЗ {len(vacancies)} ВАКАНСИЙ ЧЕРЕЗ GEMINI")
    logger.info(f"   Батчами по {batch_size} вакансий за запрос")
    logger.info("=" * 80)
    
    if not vacancies:
        logger.warning("⚠️  Список вакансий пуст!")
        return []
    
    try:
        # ========== СОБИРАЕМ ДАННЫЕ СТУДЕНТА (ОДИН РАЗ) ==========
        specialization = student_profile.education.specialization if hasattr(student_profile, 'education') else "Неизвестно"
        course = student_profile.course_number or "Неизвестно"
        gpa = float(student_profile.gpa) if student_profile.gpa else 0.0
        
        top_subjects = student_profile.academic_records.order_by('-score')[:5]
        subjects_str = ', '.join([s.subject_name for s in top_subjects]) if top_subjects.exists() else "Нет данных"

        
        practices = student_profile.practices.all()[:2]
        practices_str = ', '.join([p.practice_type for p in practices if p.practice_type]) or "Нет опыта"
        
        logger.info(f"📚 Данные студента:")
        logger.info(f"   - Специальность: {specialization}")
        logger.info(f"   - Курс: {course}")
        logger.info(f"   - GPA: {gpa}")
        
        # ========== ДЕЛИМ НА БАТЧИ И АНАЛИЗИРУЕМ ==========
        all_analyzed = []
        
        # Ограничиваем количество батчей
        batches_to_process = min(max_batches, (len(vacancies) - 1) // batch_size + 1)
        max_vacancies_to_analyze = batches_to_process * batch_size

        if max_vacancies_to_analyze < len(vacancies):
            logger.info(f"⚠️  Ограничение: будем анализировать только первые {max_vacancies_to_analyze} вакансий")
            vacancies = vacancies[:max_vacancies_to_analyze]
        
        for batch_start in range(0, len(vacancies), batch_size):
            batch_end = min(batch_start + batch_size, len(vacancies))
            batch = vacancies[batch_start:batch_end]
            
            batch_num = batch_start // batch_size + 1
            total_batches = batches_to_process
            
            logger.info("-" * 80)
            logger.info(f"📦 Батч {batch_num}/{total_batches}: вакансии {batch_start+1}-{batch_end}")
            
            # Формируем список вакансий для промпта (ТОЛЬКО ДЛЯ ЭТОГО БАТЧА)
            vacancies_list = []
            for idx, vac in enumerate(batch, 1):
                vacancies_list.append({
                    'index': idx,
                    'title': vac.get('title', 'Не указано'),
                    'company': vac.get('company', 'Не указана'),
                    'city': vac.get('city', 'Не указан'),
                    'salary': vac.get('salary', 'Не указана'),
                    'employment': vac.get('employment', 'Не указано'),
                    'snippet': vac.get('snippet', 'Нет описания')[:200],
                    'skills': ', '.join(vac.get('skills', [])[:5]) if vac.get('skills') else 'Не указаны'
                })
            
            # Формируем промпт для батча
            prompt = f"""
Ты — эксперт по карьерному консультированию в Казахстане.

ПРОФИЛЬ СТУДЕНТА:
- Специальность: {specialization}
- Курс: {course}
- Средний балл (GPA): {gpa}
- Сильные предметы: {subjects_str}
- Опыт практик: {practices_str}

СПИСОК ВАКАНСИЙ ДЛЯ АНАЛИЗА (JSON):
{json.dumps(vacancies_list, ensure_ascii=False, indent=2)}

ЗАДАЧА:
Проанализируй КАЖДУЮ вакансию и оцени соответствие студенту.

Для каждой вакансии верни оценки (от 0 до 100):
- **overall_match** - общая оценка соответствия
- **education_match** - соответствие специальности
- **skills_match** - соответствие навыков
- **experience_match** - подходит ли для студента {course} курса
- **location_match** - подходит ли локация
- **salary_match** - реалистична ли зарплата
- **reasoning** - краткое объяснение (1-2 предложения)
- **red_flags** - минусы (массив строк, может быть пустым)
- **green_flags** - плюсы (массив строк, может быть пустым)

ФОРМАТ ОТВЕТА:
Верни ТОЛЬКО JSON массив (без markdown, без пояснений):
[
  {{
    "index": 1,
    "overall_match": 85,
    "education_match": 90,
    "skills_match": 80,
    "experience_match": 85,
    "location_match": 70,
    "salary_match": 90,
    "reasoning": "Отличное совпадение для студента",
    "red_flags": ["требуется опыт"],
    "green_flags": ["обучение на месте"]
  }},
  ...
]

ВАЖНО: Верни ровно {len(batch)} объектов в массиве.
"""
            
            logger.info(f"   📤 Отправляем запрос к Gemini...")
            
            try:
                # Отправляем запрос для батча
                response = model.generate_content(prompt)
                response_text = response.text.strip()
                
                # Убираем markdown
                if response_text.startswith('```'):
                    response_text = response_text.split('```')[1]
                    if response_text.startswith('json'):
                        response_text = response_text[4:]
                    response_text = response_text.strip()
                
                # Парсим JSON
                analyses = json.loads(response_text)
                
                if not isinstance(analyses, list):
                    raise ValueError("Ответ не является массивом")
                
                logger.info(f"   ✅ Получен анализ для {len(analyses)} вакансий")
                
                # Применяем анализ к вакансиям батча
                for analysis in analyses:
                    idx = analysis.get('index', 1) - 1
                    
                    if 0 <= idx < len(batch):
                        vacancy = batch[idx].copy()
                        
                        vacancy['gemini_score'] = analysis.get('overall_match', 0)
                        vacancy['education_match'] = analysis.get('education_match', 0)
                        vacancy['skills_match'] = analysis.get('skills_match', 0)
                        vacancy['experience_match'] = analysis.get('experience_match', 0)
                        vacancy['location_match'] = analysis.get('location_match', 0)
                        vacancy['salary_match'] = analysis.get('salary_match', 0)
                        vacancy['reasoning'] = analysis.get('reasoning', '')
                        vacancy['red_flags'] = analysis.get('red_flags', [])
                        vacancy['green_flags'] = analysis.get('green_flags', [])
                        
                        all_analyzed.append(vacancy)
                        
                        score = vacancy['gemini_score']
                        title = vacancy.get('title', 'Без названия')
                        logger.info(f"   ✓ [{score}/100] {title[:50]}...")
                
            except json.JSONDecodeError as e:
                logger.error(f"   ❌ Ошибка парсинга JSON для батча {batch_num}: {e}")
                logger.error(f"      Ответ: {response_text[:300]}...")
                # Добавляем батч с нулевыми оценками
                for vac in batch:
                    vac['gemini_score'] = 0
                    vac['reasoning'] = "Ошибка анализа"
                    vac['red_flags'] = []
                    vac['green_flags'] = []
                    all_analyzed.append(vac)
            
            except Exception as e:
                logger.error(f"   ❌ Ошибка анализа батча {batch_num}: {e}")
                # Добавляем батч с нулевыми оценками
                for vac in batch:
                    vac['gemini_score'] = 0
                    vac['reasoning'] = "Ошибка анализа"
                    vac['red_flags'] = []
                    vac['green_flags'] = []
                    all_analyzed.append(vac)
        
        # ========== СОРТИРУЕМ ВСЕ РЕЗУЛЬТАТЫ ==========
        logger.info("-" * 80)
        logger.info(f"✅ Успешно проанализировано: {len(all_analyzed)} вакансий")
        
        all_analyzed.sort(key=lambda x: x.get('gemini_score', 0), reverse=True)
        
        logger.info(f"\n🏆 ТОП-5 ВАКАНСИЙ ПО ОЦЕНКЕ GEMINI:")
        for i, vac in enumerate(all_analyzed[:5], 1):
            score = vac.get('gemini_score', 0)
            title = vac.get('title', 'Без названия')
            logger.info(f"   #{i}. [{score}/100] {title}")
        
        logger.info("=" * 80)
        
        return all_analyzed
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА В BATCH-АНАЛИЗЕ")
        logger.error(f"   Тип: {type(e).__name__}")
        logger.error(f"   Сообщение: {str(e)}", exc_info=True)
        logger.error("=" * 80)
        return _fallback_vacancies(vacancies)


def _fallback_vacancies(vacancies):
    """
    Fallback: возвращает вакансии с нулевыми оценками при ошибке
    """
    logger.warning("⚠️  Используем fallback - возвращаем вакансии без анализа")
    for vac in vacancies:
        vac['gemini_score'] = 0
        vac['reasoning'] = "Ошибка анализа"
        vac['red_flags'] = []
        vac['green_flags'] = []
    return vacancies


def _fallback_vacancies(vacancies):
    """
    Fallback: возвращает вакансии с нулевыми оценками при ошибке
    """
    logger.warning("⚠️  Используем fallback - возвращаем вакансии без анализа")
    for vac in vacancies:
        vac['gemini_score'] = 0
        vac['reasoning'] = "Ошибка анализа"
        vac['red_flags'] = []
        vac['green_flags'] = []
    return vacancies