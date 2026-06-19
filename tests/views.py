import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.db import transaction
from .models import TestValores, ParteTest, PreguntaValores, OpcionValores, ResultadoValores
from .models import TestDomino, ProblemaDomino, ResultadoDomino
from users.models import CustomUser
from django.utils import timezone as django_timezone
from django.utils import timezone
from datetime import date, datetime
from django.utils import timezone as django_timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import os
import matplotlib
matplotlib.use('Agg')  # Configura el backend a Agg antes de importar pyplot
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages

logger = logging.getLogger(__name__)

@login_required
def inicio_test_valores(request):
    test = TestValores.objects.get(nombre="Test de Valores de Allport")
    primera_parte = ParteTest.objects.get(test=test, tipo='PRIMERA')
    
    return render(request, 'tests/inicio_test_valores.html', {
        'test': test,
        'primera_parte': primera_parte
    })

@login_required
def inicio_segundo_test_valores(request):
    test = TestValores.objects.get(nombre="Test de Valores de Allport")
    segunda_parte = ParteTest.objects.get(test=test, tipo='SEGUNDA')
    
    return render(request, 'tests/inicio_segunda_parte_valores.html', {
        'test': test,
        'segunda_parte': segunda_parte
    })

def primera_parte_valores(request):
    test = TestValores.objects.get(nombre="Test de Valores de Allport")
    primera_parte = ParteTest.objects.get(test=test, tipo='PRIMERA')
    preguntas = PreguntaValores.objects.filter(parte=primera_parte).order_by('id')
    
    if request.method == 'POST':
        respuestas = {}
        for key in request.POST:
            if key.startswith('puntos_p'):
                try:
                    respuestas[key] = int(request.POST[key])
                except ValueError:
                    respuestas[key] = 0
        request.session['primera_parte_respuestas'] = respuestas
        print("Respuestas primera parte guardadas:", respuestas)  # Debug
        return redirect('tests:inicio_segundo_test_valores')
    
    return render(request, 'tests/primera_parte_valores.html', {
        'test': test,
        'parte': primera_parte,
        'preguntas': preguntas,
        'total_preguntas': preguntas.count()
    })

def segunda_parte_valores(request):
    test = TestValores.objects.get(nombre="Test de Valores de Allport")
    segunda_parte = ParteTest.objects.get(test=test, tipo='SEGUNDA')
    preguntas = PreguntaValores.objects.filter(parte=segunda_parte).order_by('id')
    
    if request.method == 'POST':
        respuestas = {}
        for key in request.POST:
            if key.startswith('puntos_p'):
                try:
                    respuestas[key] = int(request.POST[key])
                except ValueError:
                    respuestas[key] = 0
        request.session['segunda_parte_respuestas'] = respuestas
        print("Respuestas segunda parte guardadas:", respuestas)  # Debug
        return redirect('tests:calcular_resultados_valores')
    
    return render(request, 'tests/segunda_parte_valores.html', {
        'test': test,
        'parte': segunda_parte,
        'preguntas': preguntas,
        'total_preguntas': preguntas.count()
    })


def calcular_resultados_valores(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    try:
        json_path = settings.BASE_DIR / 'estudio.json'
        with open(json_path, 'r', encoding='utf-8') as f:
            estudio = json.load(f)
        
        primera_parte = request.session.get('primera_parte_respuestas', {})
        segunda_parte = request.session.get('segunda_parte_respuestas', {})

        print("Respuestas primera parte:", primera_parte)
        print("Respuestas segunda parte:", segunda_parte)
        
        genero_usuario = request.user.gender if hasattr(request.user, 'gender') else 'M'

        totales_por_pagina = {}
        resultados_valores = {
            'Teórico': 0,
            'Económico': 0,
            'Estético': 0,
            'Social': 0,
            'Político': 0,
            'Religioso': 0
        }
        
        mapeo_paginas = None
        for item in estudio['criterios_calificacion']['procedimiento']:
            if isinstance(item, dict):
                mapeo_paginas = item
                break
        
        if not mapeo_paginas:
            raise ValueError("No se encontró el mapeo de páginas en el JSON")
        
        print("="*50)
        print("PRIMERA PARTE")
        print("="*50)
        for pagina_data in estudio['primera_parte']:
            num_pagina = pagina_data['pagina']
            clave_pagina = f"pagina_{num_pagina}"
            totales_por_pagina[clave_pagina] = {'R': 0.0, 'S': 0.0, 'T': 0.0, 'X': 0.0, 'Y': 0.0, 'Z': 0.0}

            print(f"\nPágina {num_pagina}:")
            
            for pregunta in pagina_data['preguntas']:
                pregunta_id = pregunta['id']
                key_a = f'puntos_p{pregunta_id}_a'
                key_b = f'puntos_p{pregunta_id}_b'
                
                try:
                    puntos_a = float(primera_parte.get(key_a, 0))
                except (TypeError, ValueError):
                    puntos_a = 0.0
                
                try:
                    puntos_b = float(primera_parte.get(key_b, 0))
                except (TypeError, ValueError):
                    puntos_b = 0.0
                
                if puntos_a == 0 and puntos_b == 0:
                    puntos_a = 1.5
                    puntos_b = 1.5
                
                for opcion in pregunta['columnas_opciones']:
                    columna = opcion['columna']
                    if opcion['letra'] == 'a':
                        totales_por_pagina[clave_pagina][columna] += puntos_a
                    else:
                        totales_por_pagina[clave_pagina][columna] += puntos_b

            for col, val in totales_por_pagina[clave_pagina].items():
                print(f"{col}: {val:.1f}")
        
        print("\n" + "="*50)
        print("SEGUNDA PARTE")
        print("="*50)
        for pagina_data in estudio['segunda_parte']:
            num_pagina = pagina_data['pagina']
            clave_pagina = f"pagina_{num_pagina}"
            totales_por_pagina[clave_pagina] = {'R': 0.0, 'S': 0.0, 'T': 0.0, 'X': 0.0, 'Y': 0.0, 'Z': 0.0}

            pregunta_14 = None
            pregunta_15 = None
            otras_preguntas = []
            
            for pregunta in pagina_data['preguntas']:
                if pregunta['id'] == 44:
                    pregunta_14 = pregunta
                elif pregunta['id'] == 45:
                    pregunta_15 = pregunta
                else:
                    otras_preguntas.append(pregunta)
            
            for pregunta in otras_preguntas:
                procesar_pregunta_segunda_parte(pregunta, segunda_parte, totales_por_pagina[clave_pagina])
            
            if genero_usuario == 'M':  
                if pregunta_14:
                    procesar_pregunta_segunda_parte(pregunta_14, segunda_parte, totales_por_pagina[clave_pagina])
            else:
                if pregunta_15:
                    procesar_pregunta_segunda_parte(pregunta_15, segunda_parte, totales_por_pagina[clave_pagina])
            print(f"\nPágina {num_pagina}:")
            for col, val in totales_por_pagina[clave_pagina].items():
                print(f"{col}: {val:.1f}")
        
        print("\n" + "="*50)
        print("SUMA POR VALORES (ANTES DE CORRECCIONES)")
        print("="*50)
        for clave_pagina, totales in totales_por_pagina.items():
            if clave_pagina in mapeo_paginas:
                mapeo = mapeo_paginas[clave_pagina]
                for columna, valor in totales.items():
                    nombre_valor = mapeo[columna]
                    resultados_valores[nombre_valor] += valor

                    print(f"{clave_pagina} - {columna} -> {nombre_valor}: {valor:.1f}")
        
        print("\n" + "="*50)
        print("RESULTADOS ANTES DE CORRECCIONES")
        print("="*50)
        for valor, puntuacion in resultados_valores.items():
            print(f"{valor}: {puntuacion:.1f}")

        correcciones = {
            'Teórico': -4,
            'Económico': -5,
            'Estético': 6,
            'Social': -1,
            'Político': 3,
            'Religioso': 1
        }

        clasificaciones = {}
    
        rangos_valores = {
            'Teórico': {'muy_bajo': 30, 'bajo': 34, 'alto': 45, 'muy_alto': 50},
            'Económico': {'muy_bajo': 28, 'bajo': 35, 'alto': 45, 'muy_alto': 51},
            'Estético': {'muy_bajo': 30, 'bajo': 35, 'alto': 46, 'muy_alto': 52},
            'Social': {'muy_bajo': 29, 'bajo': 34, 'alto': 44, 'muy_alto': 49},
            'Político': {'muy_bajo': 31, 'bajo': 35, 'alto': 48, 'muy_alto': 50},
            'Religioso': {'muy_bajo': 26, 'bajo': 33, 'alto': 48, 'muy_alto': 57},
        }
        
        significado_clinico = {
            'MUY BAJO': "Significativamente por debajo de la norma poblacional",
            'BAJO': "Por debajo del promedio poblacional",
            'NORMAL': "Dentro del rango esperado para la población",
            'ALTO': "Por encima del promedio poblacional",
            'MUY ALTO': "Significativamente por encima de la norma poblacional",
        }
        
        for valor, puntuacion in resultados_valores.items():
            rangos = rangos_valores[valor]
            
            if puntuacion < rangos['muy_bajo']:
                clasif = "MUY BAJO"
                color = "#dc3545"
            elif puntuacion < rangos['bajo']:
                clasif = "BAJO"
                color = "#ffc107"
            elif puntuacion > rangos['muy_alto']:
                clasif = "MUY ALTO"
                color = "#0dcaf0"
            elif puntuacion > rangos['alto']:
                clasif = "ALTO"
                color = "#198754"
            else:
                clasif = "NORMAL"
                color = "#2a4d6e"
                
            clasificaciones[valor] = {
                'clasificacion': clasif,
                'color': color,
                'significado': significado_clinico[clasif]
            }
        
        for valor, correccion in correcciones.items():
            resultados_valores[valor] += correccion

        print("\n" + "="*50)
        print("RESULTADOS DESPUÉS DE CORRECCIONES")
        print("="*50)
        for valor, puntuacion in resultados_valores.items():
            print(f"{valor}: {puntuacion:.1f}")
        
        valores_ordenados = sorted(
            resultados_valores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        valor_dominante = valores_ordenados[0][0]
        
        descripcion_valor = next(
            (v['descripcion'] for v in estudio['interpretacion_valores']['valores'] 
            if v['nombre'] == valor_dominante
        ))
        
        meta_valor = next(
            (v['meta'] for v in estudio['interpretacion_valores']['valores'] 
            if v['nombre'] == valor_dominante
        ))
        
        with transaction.atomic():
            test = TestValores.objects.get(nombre="Test de Valores de Allport")
            usuario = CustomUser.objects.get(id=request.user.id)
            
            resultado = ResultadoValores(
                usuario=usuario,
                test=test,
                teorico=resultados_valores['Teórico'],
                economico=resultados_valores['Económico'],
                estetico=resultados_valores['Estético'],
                social=resultados_valores['Social'],
                politico=resultados_valores['Político'],
                religioso=resultados_valores['Religioso'],
                clasificaciones=clasificaciones,
                valor_dominante=valor_dominante,
                descripcion_dominante=descripcion_valor,
                meta_dominante=meta_valor,
                rangos_valores=rangos_valores
            )
            resultado.save()
        
        request.session['resultados_valores'] = {
            'valores': resultados_valores,
            'dominante': valor_dominante,
            'descripcion': descripcion_valor,
            'meta': meta_valor,
            'clasificaciones': clasificaciones,  # Nuevo dato
            'rangos_valores': rangos_valores,    # Nuevo dato
        }
        
        request.session.pop('primera_parte_respuestas', None)
        request.session.pop('segunda_parte_respuestas', None)

        request.session['resultado_id'] = resultado.id
        
        return redirect('tests:mostrar_resultados_valores')
    
    except Exception as e:
        logger.exception("Error al calcular resultados")
        return render(request, 'error.html', {'error': str(e)})

def procesar_pregunta_segunda_parte(pregunta, respuestas, totales_pagina):
    pregunta_id = pregunta['id']
    puntos = {}
    omitida = True
    
    for opcion in pregunta['columnas_opciones']:
        letra = opcion['letra']
        key = f'puntos_p{pregunta_id}_{letra}'
        
        try:
            valor = float(respuestas.get(key, 0))
        except (TypeError, ValueError):
            valor = 0.0
        
        puntos[letra] = valor
        if valor != 0:
            omitida = False
    
    if omitida:
        for opcion in pregunta['columnas_opciones']:
            puntos[opcion['letra']] = 2.5
    
    for opcion in pregunta['columnas_opciones']:
        columna = opcion['columna']
        totales_pagina[columna] += puntos[opcion['letra']]

def mostrar_resultados_valores(request):
    resultados = request.session.pop('resultados_valores', None)
    resultado_id = request.session.get('resultado_id')
    
    if not resultados:
        return redirect('home')
    
    try:
        resultado = ResultadoValores.objects.get(id=resultado_id)
    except ResultadoValores.DoesNotExist:
        return redirect('home')
    
    valores = ['Teórico', 'Económico', 'Estético', 'Social', 'Político', 'Religioso']
    puntuaciones = [resultados['valores'][v] for v in valores]

    colores_grafica = [resultados['clasificaciones'][v]['color'] for v in valores]
    
    context = {
        'valores': resultados['valores'],
        'dominante': resultados['dominante'],
        'descripcion': resultados['descripcion'],
        'meta': resultados['meta'],
        'clasificaciones': resultados['clasificaciones'],
        'rangos_valores': resultados['rangos_valores'],
        'valores_grafica': valores,
        'puntuaciones_grafica': puntuaciones,
        'colores_grafica_json': json.dumps(colores_grafica),
        'rangos_valores_json': json.dumps(resultados['rangos_valores']),
        'resultado_id': resultado_id,
    }
    
    response = render(request, 'tests/resultados_valores.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def generar_pdf_valores(request, resultado_id):
    try:
        resultado = ResultadoValores.objects.get(id=resultado_id)
    except ResultadoValores.DoesNotExist:
        return HttpResponse("No hay resultados disponibles", status=404)
    
    valoress = ['Teórico', 'Económico', 'Estético', 'Social', 'Político', 'Religioso']
    puntuaciones = [
        resultado.teorico,
        resultado.economico,
        resultado.estetico,
        resultado.social,
        resultado.politico,
        resultado.religioso
    ]
    
    num_vars = len(valoress)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    puntuaciones += puntuaciones[:1]  # Cerrar el círculo
    angles += angles[:1]  # Cerrar los ángulos
    
    plt.figure(figsize=(8, 8), facecolor='white')
    ax = plt.subplot(111, polar=True, facecolor='#f8f9fa')

    ax.spines['polar'].set_visible(False)
    ax.grid(color='gray', linestyle='-', linewidth=0.5, alpha=0.3)

    ax.plot(angles, puntuaciones, color='#3A7D7D', linewidth=2, marker='o', 
            markersize=8, markerfacecolor='#3A7D7D', markeredgecolor='white', 
            markeredgewidth=1.5)
            
    ax.fill(angles, puntuaciones, color='#3A7D7D', alpha=0.1)

    plt.xticks(angles[:-1], valoress, fontsize=10, fontweight='bold', color='#333')
    
    plt.title('Perfil de Valores', fontsize=14, fontweight='bold', pad=20)
    
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close()
    buffer.seek(0)
    
    image_png = buffer.getvalue()
    buffer.close()
    grafico_base64 = base64.b64encode(image_png).decode('utf-8')

    valores = {
        'Teórico': resultado.teorico,
        'Económico': resultado.economico,
        'Estético': resultado.estetico,
        'Social': resultado.social,
        'Político': resultado.politico,
        'Religioso': resultado.religioso,
    }

    context = {
        'valores': valores,
        'dominante': resultado.valor_dominante,
        'descripcion': resultado.descripcion_dominante,
        'meta': resultado.meta_dominante,
        'clasificaciones': resultado.clasificaciones,
        'rangos_valores': resultado.rangos_valores,
        'grafico_base64': grafico_base64,
        'static_path': os.path.join(settings.BASE_DIR, 'psycho_platform', 'static'),
        'resultado_id': resultado_id
    }
    
    template_path = 'tests/reporte_valores.html'
    template = get_template(template_path)
    html = template.render(context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_valores.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF: %s' % html)
    return response

@login_required
def inicio_domino(request):
    test = TestDomino.objects.get(nombre="Test de Dominó D-48")
    return render(request, 'tests/inicio_domino.html', {
        'test': test
    })

def test_domino(request):
    request.session['tiempo_inicio_domino'] = timezone.now().timestamp()
    numeros_problemas = list(range(1, 49))
    
    problemas = ProblemaDomino.objects.filter(
        numero__in=numeros_problemas
    ).order_by('numero')
    
    problemas_preparados = []
    for problema in problemas:
        preparado = {'obj': problema, 'tipo': problema.tipo}
        
        if problema.tipo == 'MATRIZ':
            matriz = [[None] * problema.matriz_columnas for _ in range(problema.matriz_filas)]
            for ficha_data in problema.fichas:
                fila = ficha_data['fila']
                columna = ficha_data['columna']
                matriz[fila][columna] = ficha_data
            preparado['matriz'] = matriz
        
        elif problema.tipo in ['FLOR', 'ESPIRAL']:
            preparado['config'] = problema.configuracion_extra
            preparado['fichas'] = problema.fichas
        
        problemas_preparados.append(preparado)
    
    return render(request, 'tests/test_domino.html', {
        'problemas_preparados': problemas_preparados
    })

def detalle_problema_domino(request, problema_id):
    problema = get_object_or_404(ProblemaDomino, id=problema_id)
    
    matriz = [[None for _ in range(problema.matriz_columnas)] 
              for _ in range(problema.matriz_filas)]
    
    for ficha_data in problema.fichas:
        fila = ficha_data['fila']
        columna = ficha_data['columna']
        matriz[fila][columna] = ficha_data
    
    return render(request, 'tests/detalle_problema_domino.html', {
        'problema': problema,
        'matriz': matriz
    })

def calcular_resultados_domino(request):
    if request.method == 'POST':
        tiempo_inicio_ts = request.session.get('tiempo_inicio_domino')
        if tiempo_inicio_ts:
            tiempo_inicio = datetime.fromtimestamp(tiempo_inicio_ts)
            tiempo_inicio = django_timezone.make_aware(tiempo_inicio)
            tiempo_utilizado = (django_timezone.now() - tiempo_inicio).total_seconds()
        else:
            tiempo_utilizado = 0

        fecha_nacimiento = request.user.date_of_birth
        
        grupo_edad = 'general'
        
        if fecha_nacimiento:
            hoy = date.today()
            edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
            
            if 12 <= edad <= 13:
                grupo_edad = '12-13'
            elif 14 <= edad <= 15:
                grupo_edad = '14-15'
            elif 16 <= edad <= 17:
                grupo_edad = '16-17'
            elif 18 <= edad <= 30:
                grupo_edad = '18-30'
        baremo_edad ={}
        if grupo_edad == '12-13':
            baremo_edad = {
                42: 99, 38: 95, 35: 90, 32: 80, 31: 75, 30: 70, 
                29: 60, 27: 50, 25: 40, 22: 30, 21: 25, 20: 20,
                14: 10, 9: 5, 4: 1
            }
        elif grupo_edad == '14-15':
            baremo_edad = {
                43: 99, 39: 95, 37: 90, 33: 80, 32: 75, 31: 70,
                30: 60, 28: 50, 26: 40, 23: 30, 22: 25, 21: 20,
                15: 10, 11: 5, 5: 1
            }
        elif grupo_edad == '16-17':
            baremo_edad = {
                44: 99, 41: 95, 39: 90, 35: 80, 34: 75, 33: 70,
                32: 60, 29: 50, 27: 40, 24: 30, 23: 25, 22: 20,
                16: 10, 12: 5, 6: 1
            }
        elif grupo_edad == '18-30':
            baremo_edad = {
                45: 99, 41: 95, 40: 90, 37: 80, 36: 75, 35: 70,
                33: 60, 31: 50, 29: 40, 26: 30, 25: 25, 24: 20,
                20: 10, 16: 5, 8: 1
            }
        else:
            baremo_edad = {
                44: 99, 40: 95, 37: 90, 35: 80, 34: 75, 33: 70, 
                31: 60, 29: 50, 27: 40, 25: 30, 23: 25, 22: 20,
                17: 10, 12: 5, 5: 1
            }

        respuestas_usuario = {}
        
        problemas = ProblemaDomino.objects.filter(numero__in=range(1, 49))
        correctas = 0
        intentadas = 0
        
        for problema in problemas:
            key_sup = f'problema_{problema.id}_superior'
            key_inf = f'problema_{problema.id}_inferior'
            user_sup = request.POST.get(key_sup, '')
            user_inf = request.POST.get(key_inf, '')
            correcta_sup, correcta_inf = problema.respuesta
            es_correcta = False
            
            if user_sup.isdigit() and user_inf.isdigit():
                intentadas += 1
                user_sup = int(user_sup)
                user_inf = int(user_inf)
                
                if user_sup == correcta_sup and user_inf == correcta_inf:
                    correctas += 1
                    es_correcta = True
            
            respuestas_usuario[problema.numero] = {
                'respuesta_usuario': f"{user_sup}/{user_inf}",
                'respuesta_correcta': f"{correcta_sup}/{correcta_inf}",
                'correcta': es_correcta
            }

        puntuacion = correctas
        eficiencia = (correctas / intentadas * 100) if intentadas > 0 else 0
        
        percentil = 0
        for puntos, perc in baremo_edad.items():
            if puntuacion >= puntos:
                percentil = perc
                break
        
        if percentil >= 95:
            diagnostico = "Superior"
        elif percentil >= 75:
            diagnostico = "Superior a término medio"
        elif percentil >= 50:
            diagnostico = "Término medio"
        elif percentil >= 25:
            diagnostico = "Inferior al término medio"
        else:
            diagnostico = "Deficiente"
        
        test = TestDomino.objects.get(nombre="Test de Dominó D-48")
        resultado = ResultadoDomino(
            usuario=request.user,
            test=test,
            fecha=timezone.now(),
            respuestas=respuestas_usuario,
            puntuacion=puntuacion,
            percentil=percentil,
            tiempo_utilizado=tiempo_utilizado,
            eficiencia=eficiencia,
            diagnostico=diagnostico,
            baremo=baremo_edad,
            grupo_edad=grupo_edad
        )
        resultado.save()
        
        return redirect('tests:resultados_domino', resultado_id=resultado.id)
    
    return redirect('tests:test_domino')

def resultados_domino(request, resultado_id):
    resultado = get_object_or_404(ResultadoDomino, id=resultado_id)
    return render(request, 'tests/resultados_domino.html', {'resultado': resultado})

def generar_pdf_domino(request, resultado_id):
    resultado = get_object_or_404(ResultadoDomino, id=resultado_id)
    
    puntuacion = resultado.puntuacion
    percentil = resultado.percentil
    eficiencia = resultado.eficiencia
    
    puntuacion_normalizada = (puntuacion / 48) * 100
    percentil_normalizado = percentil
    eficiencia_normalizada = eficiencia
    
    labels = ['Puntuación', 'Percentil', 'Eficiencia']
    data = [puntuacion_normalizada, percentil_normalizado, eficiencia_normalizada]
    
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    data += data[:1]  # Cerrar el círculo
    angles += angles[:1]  # Cerrar los ángulos

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.set_facecolor('white')
    ax.set_facecolor('#f8f9fa')

    ax.plot(angles, data, color='#3A7D7D', linewidth=2, marker='o', 
            markersize=8, markerfacecolor='#3A7D7D', markeredgecolor='white', 
            markeredgewidth=1.5)
    ax.fill(angles, data, color='#3A7D7D', alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10, fontweight='bold', color='#333')
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_yticklabels(["0", "20", "40", "60", "80", "100"], color="gray", size=8)
    ax.set_ylim(0, 100)
    ax.set_title('Rendimiento en el Test de Dominó', fontsize=14, fontweight='bold', pad=20)
    
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    
    image_png = buffer.getvalue()
    buffer.close()
    grafico_base64 = base64.b64encode(image_png).decode('utf-8')

    context = {
        'resultado': resultado,
        'grafico_base64': grafico_base64,
        'static_path': os.path.join(settings.BASE_DIR, 'psycho_platform', 'static'),
    }
    
    template_path = 'tests/reporte_domino.html'
    template = get_template(template_path)
    html = template.render(context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_domino_{resultado_id}.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF: %s' % html)
    return response

def test_index(request):
    """Vista para la página de inicio de la plataforma de pruebas"""
    return render(request, 'tests/index.html')

import time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def health_check(request):
    """Endpoint simple para mantener la app activa"""
    return JsonResponse({
        "status": "ok",
        "timestamp": time.time(),
        "message": "PsyMetrics is alive",
        "app": "psymetrics"
    })