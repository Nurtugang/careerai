import logging
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger('core')


class VacancyRecommender:
    """
    Рекомендательная система вакансий на основе TF-IDF и Cosine Similarity
    """
    
    def __init__(self):
        logger.info("=" * 80)
        logger.info("VacancyRecommender: Инициализация рекомендательной системы")
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            ngram_range=(1, 2),
            min_df=1
        )
        logger.info("VacancyRecommender: TfidfVectorizer создан (max_features=500, ngram_range=(1,2))")
    
    def _build_student_text(self, student_profile):
        """
        Формируем текстовое представление студента
        """
        logger.info("-" * 80)
        logger.info(f"📚 Начинаем сбор данных студента (ID: {student_profile.person_id})")
        
        parts = []
        
        # Базовая информация об образовании
        try:
            education = student_profile.education
            logger.info(f"  ✓ Получаем информацию об образовании...")
            
            if education.profession:
                parts.append(education.profession)
                logger.info(f"    - Профессия: {education.profession}")
            
            if education.specialization:
                parts.append(education.specialization)
                logger.info(f"    - Специализация: {education.specialization}")
            
            if education.qualification:
                parts.append(education.qualification)
                logger.info(f"    - Квалификация: {education.qualification}")
                
        except Exception as e:
            logger.warning(f"  ✗ Ошибка при получении образования: {e}")
        
        # Предметы (берем только с оценками, без null)
        try:
            records = student_profile.academic_records.filter(
                grade__isnull=False
            ).exclude(grade='')
            
            total_subjects = records.count()
            logger.info(f"  ✓ Получаем предметы студента (всего с оценками: {total_subjects})")
            
            subjects_by_grade = {'A': [], 'B': [], 'C': [], 'Other': []}
            
            for record in records:
                subject = record.subject_name.strip()
                grade = record.grade
                
                # Добавляем название предмета несколько раз в зависимости от оценки
                if grade in ['A', 'A-', 'B+']:
                    parts.extend([subject] * 3)
                    subjects_by_grade['A'].append(f"{subject} ({grade})")
                elif grade in ['B', 'B-']:
                    parts.extend([subject] * 2)
                    subjects_by_grade['B'].append(f"{subject} ({grade})")
                elif grade in ['C', 'C+', 'C-']:
                    parts.append(subject)
                    subjects_by_grade['C'].append(f"{subject} ({grade})")
                else:
                    parts.append(subject)
                    subjects_by_grade['Other'].append(f"{subject} ({grade})")
            
            # Логируем предметы по категориям
            if subjects_by_grade['A']:
                logger.info(f"    - Отличные оценки (вес x3): {', '.join(subjects_by_grade['A'][:5])}{'...' if len(subjects_by_grade['A']) > 5 else ''}")
            if subjects_by_grade['B']:
                logger.info(f"    - Хорошие оценки (вес x2): {', '.join(subjects_by_grade['B'][:5])}{'...' if len(subjects_by_grade['B']) > 5 else ''}")
            if subjects_by_grade['C']:
                logger.info(f"    - Средние оценки (вес x1): {', '.join(subjects_by_grade['C'][:5])}{'...' if len(subjects_by_grade['C']) > 5 else ''}")
                
        except Exception as e:
            logger.warning(f"  ✗ Ошибка при получении предметов: {e}")
        
        # Практики
        try:
            practices = student_profile.practices.all()
            practice_count = practices.count()
            logger.info(f"  ✓ Получаем практики студента (всего: {practice_count})")
            
            for practice in practices:
                if practice.practice_type:
                    parts.append(practice.practice_type)
                    logger.info(f"    - Практика: {practice.practice_type}")
                if practice.position:
                    parts.append(practice.position)
                    logger.info(f"      Должность: {practice.position}")
        except Exception as e:
            logger.warning(f"  ✗ Ошибка при получении практик: {e}")
        
        final_text = ' '.join(parts)
        logger.info(f"  ✓ Итоговый текст студента собран (длина: {len(final_text)} символов, {len(parts)} элементов)")
        logger.info(f"  📝 Превью текста студента:")
        logger.info(f"     {final_text}")
        
        return final_text
    
    def _build_vacancy_text(self, vacancy):
        """
        Формируем текстовое представление вакансии
        """
        parts = []
        
        # Название вакансии (важнее всего)
        if vacancy.get('title'):
            parts.extend([vacancy['title']] * 3)
        
        # Компания
        if vacancy.get('company'):
            parts.append(vacancy['company'])
        
        # Навыки (очень важны)
        if vacancy.get('skills'):
            for skill in vacancy['skills']:
                parts.extend([skill] * 2)
        
        # Описание
        if vacancy.get('snippet'):
            snippet = vacancy['snippet'].replace('<highlighttext>', '').replace('</highlighttext>', '')
            parts.append(snippet)
        
        return ' '.join(parts)
    
    def get_recommendations(self, student_profile, vacancies, top_n=10):
        """
        Получить топ-N рекомендованных вакансий для студента
        """
        logger.info("=" * 80)
        logger.info("🎯 ЗАПУСК РЕКОМЕНДАТЕЛЬНОЙ СИСТЕМЫ")
        logger.info("=" * 80)
        
        if not vacancies:
            logger.warning("⚠️  Список вакансий пуст! Возвращаем пустой список.")
            return []
        
        logger.info(f"📊 Входные данные:")
        logger.info(f"  - Всего вакансий получено: {len(vacancies)}")
        logger.info(f"  - Нужно вернуть топ: {top_n}")
        logger.info(f"  - Профиль студента: {'Есть' if student_profile else 'Отсутствует'}")
        
        if not student_profile:
            logger.warning("⚠️  Профиль студента не передан. Возвращаем первые 10 вакансий БЕЗ рекомендаций.")
            return vacancies[:top_n]
        
        try:
            # Строим текст студента
            logger.info("")
            student_text = self._build_student_text(student_profile)
            
            if not student_text.strip():
                logger.error(f"❌ Текст студента пуст! Возвращаем вакансии без рекомендаций.")
                return vacancies[:top_n]
            
            # Строим тексты вакансий
            logger.info("-" * 80)
            logger.info(f"💼 Обрабатываем вакансии...")
            vacancy_texts = []
            
            for idx, vacancy in enumerate(vacancies, 1):
                v_text = self._build_vacancy_text(vacancy)
                vacancy_texts.append(v_text)
                
                if idx <= 3:  # Логируем первые 3 вакансии подробно
                    logger.info(f"  Вакансия #{idx}: {vacancy.get('title', 'Без названия')}")
                    logger.info(f"    - Компания: {vacancy.get('company', 'Не указана')}")
                    logger.info(f"    - Навыки: {', '.join(vacancy.get('skills', [])[:5])}{'...' if len(vacancy.get('skills', [])) > 5 else ''}")
                    logger.info(f"    - Длина текста: {len(v_text)} символов")
            
            if len(vacancies) > 3:
                logger.info(f"  ... и еще {len(vacancies) - 3} вакансий")
            
            # TF-IDF векторизация
            logger.info("-" * 80)
            logger.info("🔢 Векторизация текстов (TF-IDF)...")
            all_texts = [student_text] + vacancy_texts
            logger.info(f"  - Всего текстов для векторизации: {len(all_texts)}")
            
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            logger.info(f"  ✓ Матрица TF-IDF создана: {tfidf_matrix.shape}")
            logger.info(f"    (строки=тексты, столбцы=признаки)")
            
            # Cosine Similarity
            logger.info("-" * 80)
            logger.info("📐 Вычисляем Cosine Similarity...")
            student_vector = tfidf_matrix[0:1]
            vacancy_vectors = tfidf_matrix[1:]
            
            similarities = cosine_similarity(student_vector, vacancy_vectors)[0]
            logger.info(f"  ✓ Similarity вычислен для {len(similarities)} вакансий")
            
            # Добавляем similarity score к вакансиям
            logger.info("-" * 80)
            logger.info("📊 Результаты похожести (Similarity Scores):")
            
            for i, vacancy in enumerate(vacancies):
                score = float(similarities[i])
                vacancy['similarity_score'] = score * 100
            
            # Сортируем по similarity
            sorted_vacancies = sorted(
                vacancies, 
                key=lambda x: x['similarity_score'], 
                reverse=True
            )
            
            # Логируем топ-10 вакансий с их скорами
            logger.info("")
            logger.info("🏆 ТОП-10 РЕКОМЕНДОВАННЫХ ВАКАНСИЙ:")
            for idx, vacancy in enumerate(sorted_vacancies[:10], 1):
                score = vacancy['similarity_score']
                title = vacancy.get('title', 'Без названия')
                company = vacancy.get('company', 'Неизвестно')
                logger.info(f"  #{idx}. [{score:.4f}] {title} - {company}")
            
            logger.info("-" * 80)
            logger.info(f"✅ Рекомендации успешно сгенерированы для студента {student_profile.person_id}")
            logger.info(f"   Возвращаем топ-{top_n} вакансий")
            logger.info("=" * 80)
            
            return sorted_vacancies[:top_n]
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА В РЕКОМЕНДАТЕЛЬНОЙ СИСТЕМЕ")
            logger.error(f"   Тип ошибки: {type(e).__name__}")
            logger.error(f"   Сообщение: {str(e)}", exc_info=True)
            logger.error(f"   Возвращаем вакансии БЕЗ рекомендаций")
            logger.error("=" * 80)
            return vacancies[:top_n]