from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .services import get_hh_vacancies
import json

def index(request):
    student_profile = None
    if request.user.is_authenticated:
        try:
            student_profile = request.user.student_profile
        except:
            student_profile = None
    
    MAX_QUERIES = 3
    MAX_VACANCIES = 100
    BATCH_COUNT = 1
    
    # Получаем ВСЕ проанализированные вакансии
    all_vacancies = get_hh_vacancies(
        student_profile=student_profile, 
        per_page=MAX_VACANCIES,
        max_queries=MAX_QUERIES,
        batch_count=BATCH_COUNT
    )
    
    # Сохраняем в сессию (для подгрузки еще)
    request.session['cached_vacancies'] = all_vacancies
    request.session['current_offset'] = 10
    
    # Показываем первые 10
    initial_vacancies = all_vacancies[:10]
    
    context = {
        'recommendations': initial_vacancies,
        'has_more': len(all_vacancies) > 10,
        'total_count': len(all_vacancies),
    }
    
    return render(request, 'index.html', context)


@require_http_methods(["POST"])
def load_more_vacancies(request):
    """
    API endpoint для подгрузки следующих вакансий
    """
    try:
        # Получаем кешированные вакансии из сессии
        cached_vacancies = request.session.get('cached_vacancies', [])
        current_offset = request.session.get('current_offset', 10)
        
        if not cached_vacancies:
            return JsonResponse({
                'success': False,
                'message': 'Кеш пуст. Обновите страницу.'
            })
        
        # Берем следующие 10 вакансий
        next_batch = cached_vacancies[current_offset:current_offset + 10]
        
        # Обновляем offset в сессии
        request.session['current_offset'] = current_offset + 10
        
        # Проверяем, есть ли еще вакансии
        has_more = len(cached_vacancies) > (current_offset + 10)
        
        return JsonResponse({
            'success': True,
            'vacancies': next_batch,
            'has_more': has_more,
            'loaded': len(next_batch),
            'total': len(cached_vacancies),
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Ошибка: {str(e)}'
        })

def about(request):
    return render(request, 'about.html')

def presentation(request):
    return render(request, 'presentation.html')