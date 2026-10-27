from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.classifier.models import AnalysisRecord
from .forms import UserRegisterForm

def register_view(request):
    """Registro de nuevos usuarios."""
    if request.user.is_authenticated:
        return redirect('classifier:analyze')

    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, f"¡Bienvenido a MangoLeaf-AI, {user.first_name or user.username}! Tu cuenta ha sido creada.")
            login(request, user)
            return redirect('classifier:analyze')
    else:
        form = UserRegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """Inicio de sesión de usuarios."""
    if request.user.is_authenticated:
        return redirect('classifier:analyze')

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Sesión iniciada correctamente. ¡Hola, {user.first_name or user.username}!")
                next_url = request.GET.get('next')
                return redirect(next_url if next_url else 'classifier:analyze')
        messages.error(request, "Nombre de usuario o contraseña incorrectos.")
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Cierre de sesión."""
    logout(request)
    messages.info(request, "Has cerrado sesión satisfactoriamente.")
    return redirect('core:home')


@login_required
def profile_view(request):
    """Perfil de usuario y estadísticas personales."""
    user = request.user
    user_records = AnalysisRecord.objects.filter(user=user)
    total_analyzed = user_records.count()
    healthy_count = user_records.filter(is_healthy=True).count()
    diseased_count = user_records.filter(is_healthy=False).count()

    recent_records = user_records[:5]

    return render(request, 'accounts/profile.html', {
        'total_analyzed': total_analyzed,
        'healthy_count': healthy_count,
        'diseased_count': diseased_count,
        'recent_records': recent_records,
    })
