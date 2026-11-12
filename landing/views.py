from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from .forms import ContactoForm
from courses.models import Curso  # Asegúrate de mantener la importación de tu modelo Curso

def home(request):
    cursos = Curso.objects.filter(publicado=True).order_by('-creado_en')[:4]

    if request.method == 'POST':
        form = ContactoForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            email = form.cleaned_data['email']
            telefono = form.cleaned_data.get('telefono', '')
            servicio = form.cleaned_data.get('servicio', '')
            mensaje_cliente = form.cleaned_data['mensaje']

            asunto = f"Nuevo contacto desde la Landing Page: {nombre}"
            mensaje = f"""
Has recibido una nueva solicitud de contacto desde la página principal:

Nombre: {nombre}
Correo electrónico: {email}
Teléfono: {telefono if telefono else 'No proporcionado'}
Servicio de interés: {servicio if servicio else 'No especificado'}

Mensaje:
{mensaje_cliente}
            """

            send_mail(
                asunto,
                mensaje,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=False,
            )
            messages.success(request, '¡Gracias por escribirnos! Hemos recibido tu mensaje y te responderemos pronto.')
            
            # Si en tu urls.py global tienes app_name = 'landing', usa redirect('landing:home')
            # De lo contrario, usa redirect('home'):
            return redirect('home')
        else:
            messages.error(request, 'Por favor corrige los datos ingresados en el formulario.')
    else:
        form = ContactoForm()

    return render(request, 'landing/home.html', {
        'cursos': cursos,
        'form': form,
    })
    
def nosotros(request):
    return render(request, 'landing/nosotros.html')

def servicios(request):
    if request.method == 'POST':
        form = ContactoForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            email = form.cleaned_data['email']
            telefono = form.cleaned_data.get('telefono', '')
            servicio = form.cleaned_data.get('servicio', '')
            mensaje_cliente = form.cleaned_data['mensaje']

            asunto = f"Solicitud de información (Servicios): {nombre}"
            mensaje = f"""
Has recibido un nuevo mensaje desde la página de Servicios:

Nombre: {nombre}
Correo electrónico: {email}
Teléfono: {telefono if telefono else 'No proporcionado'}
Servicio de interés: {servicio if servicio else 'No especificado'}

Mensaje:
{mensaje_cliente}
            """

            send_mail(
                asunto,
                mensaje,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=False,
            )
            messages.success(request, '¡Gracias por escribirnos! Hemos recibido tu solicitud correctamente.')
            
            # Cambia a 'landing:servicios' si usas namespace en urls.py
            return redirect('servicios')
        else:
            messages.error(request, 'Por favor corrige los datos ingresados en el formulario.')
    else:
        form = ContactoForm()

    return render(request, 'landing/servicios.html', {'form': form})
