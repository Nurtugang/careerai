import logging
import requests
from datetime import datetime

from shakarim_career_ai import settings
from django.contrib.auth.models import User
from django.contrib.auth.backends import BaseBackend

from users.models import StudentProfile, EducationInfo, AcademicRecord, PracticeExperience

logger = logging.getLogger('users')

class APILoginBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        API_URL = settings.EXTERNAL_API_URL
        
        try:
            response = requests.post(API_URL, json={"login": username, "password": password}, timeout=5)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            return None

        if data.get("status") != "success" or not data.get("success"):
            return None
        
        if data.get("person") != "student":
            if request:
                request.session['login_error'] = 'Вы не являетесь студентом. Вход запрещен.'
            return None

        person_id = data.get("personid")
        if not person_id:
            return None

        user, created = User.objects.get_or_create(username=person_id)

        if created:
            user.set_unusable_password()

        user.first_name = data.get("firstname", "")
        user.last_name = data.get("lastname", "")
        user.email = data.get("mail", "")
        user.save()
        
        profile, _ = StudentProfile.objects.update_or_create(
            user=user,
            defaults={
                'person_id': person_id,
                'lastname_en': data.get('lastname_en', ''),
                'firstname_en': data.get('firstname_en', ''),
                'patronymic': data.get('patronymic', ''),
                'patronymic_en': data.get('patronymic_en', ''),
                'phone': data.get('phone', ''),
                'birthdate': data.get('birthdate', ''),
            }
        )
        
        self._fetch_and_save_student_data(profile, person_id)
        
        if request:
            request.session['api_user_data'] = data

        return user

    def _fetch_and_save_student_data(self, profile, student_id):
        """
        Получает данные студента из второго API и сохраняет в БД
        """
        API_URL = settings.STUDENT_DATA_API_URL
        API_TOKEN = settings.STUDENT_DATA_API_TOKEN
        
        try:
            response = requests.get(
                API_URL, 
                params={'studentid': student_id, 'token': API_TOKEN},
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('status') != 'success':
                return
            
            data = result.get('data', {})
            
            student_info = data.get('studentInfo', {})
            profile.gpa = student_info.get('gpa')
            profile.course_number = student_info.get('courseNumber')
            profile.city = student_info.get('city', '')
            profile.living_address = student_info.get('livingAddress', '')
            profile.save()
            
            education_info = data.get('educationInfo', {})
            EducationInfo.objects.update_or_create(
                student=profile,
                defaults={
                    'profession': education_info.get('profession', ''),
                    'degree': education_info.get('degree', ''),
                    'qualification': education_info.get('qualification', ''),
                    'specialization': education_info.get('specialization', ''),
                    'group_name': education_info.get('groupName', ''),
                    'adviser_full_name': education_info.get('adviserFullName', ''),
                    'education_program_form': education_info.get('educationProgramForm', ''),
                }
            )
            
            AcademicRecord.objects.filter(student=profile).delete()
            for record in data.get('academicPerformance', []):
                if record.get('subjectName'):
                    AcademicRecord.objects.create(
                        student=profile,
                        subject_name=record.get('subjectName', '').strip(),
                        credits=record.get('credits', 0),
                        grade=record.get('grade'),
                        score=record.get('score')
                    )
            
            PracticeExperience.objects.filter(student=profile).delete()
            for practice in data.get('practicalExperience', []):
                start_date = self._parse_date(practice.get('startDate'))
                end_date = self._parse_date(practice.get('endDate'))
                
                PracticeExperience.objects.create(
                    student=profile,
                    organization=practice.get('organization'),
                    position=practice.get('position', ''),
                    start_date=start_date,
                    end_date=end_date,
                    practice_type=practice.get('practiceType', '')
                )
                
        except requests.RequestException as e:
            logger.error(f"Ошибка получения данных студента {student_id}: {e}", exc_info=True)
    
    def _parse_date(self, date_string):
        """
        Парсит дату из строки формата YYYY-MM-DD
        """
        if not date_string:
            return None
        try:
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None