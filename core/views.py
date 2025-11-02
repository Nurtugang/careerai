from django.shortcuts import render
from .services import get_hh_vacancies

def index(request):
    student_profile = None
    if request.user.is_authenticated:
        try:
            student_profile = request.user.student_profile
        except:
            student_profile = None
    
    hh_vacancies = get_hh_vacancies(student_profile=student_profile)
    
    context = {
        'recommendations': hh_vacancies,
    }
    
    return render(request, 'index.html', context)