from django.shortcuts import render
from courses.models import Curso

def home(request):
    cursos = Curso.objects.filter(publicado=True).order_by('-creado_en')[:4]
    return render(request, 'landing/home.html', {'cursos': cursos})

def nosotros(request):
    return render(request, 'landing/nosotros.html')

def servicios(request):
    return render(request, 'landing/servicios.html')