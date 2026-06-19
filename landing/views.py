from django.shortcuts import render

def home(request):
    return render(request, 'landing/home.html')

def nosotros(request):
    return render(request, 'landing/nosotros.html')

def servicios(request):
    return render(request, 'landing/servicios.html')