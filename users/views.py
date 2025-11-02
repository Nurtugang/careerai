from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

def login_view(request):
    error_message = None
    if 'login_error' in request.session:
        error_message = request.session.pop('login_error')

    if request.method == 'POST':
        login_id = request.POST.get('login')
        password = request.POST.get('password')

        user = authenticate(request, username=login_id, password=password)

        if user is not None:
            login(request, user)
            return redirect('profile')
        else:
            if 'login_error' in request.session:
                error_message = request.session.pop('login_error')
            else:
                error_message = "Неверный логин или пароль."

    return render(request, 'login.html', {'error_message': error_message})

@login_required
def profile_view(request):
    try:
        profile = request.user.student_profile
    except:
        profile = None
    
    return render(request, 'profile.html', {'profile': profile})

def logout_view(request):
    logout(request)
    return redirect('login')