# tests/management/commands/load_domino_data.py
import json
import os
from django.core.management.base import BaseCommand
from tests.models import TestDomino, ProblemaDomino

class Command(BaseCommand):
    help = 'Carga problemas de dominó desde un archivo JSON'

    def handle(self, *args, **options):
        # Ruta al archivo JSON (ajusta según tu estructura)
        json_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'problemas_domino.json')
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Crear/actualizar el test principal
            test, created = TestDomino.objects.update_or_create(
                nombre=data['test'],
                defaults={
                    'tiempo_limite': data['tiempo_limite'],
                    'instrucciones': data['instrucciones'],
                    'tipo_disposicion': 'MATRIZ'  # Valor por defecto
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Test creado: {test.nombre}'))
            else:
                self.stdout.write(self.style.WARNING(f'Test actualizado: {test.nombre}'))
            
            # Cargar problemas
            total_problemas = 0
            for problema_data in data['problemas']:
                # Guardar configuraciones especiales
                configuracion_extra = None
                if problema_data['tipo'] == 'FLOR':
                    configuracion_extra = problema_data.get('configuracion_floral')
                elif problema_data['tipo'] == 'ESPIRAL':
                    configuracion_extra = problema_data.get('configuracion_espiral')
                
                # Crear problema
                ProblemaDomino.objects.update_or_create(
                    test=test,
                    numero=problema_data['numero'],
                    defaults={
                        'tipo': problema_data['tipo'],
                        'matriz_filas': problema_data.get('matriz_filas'),
                        'matriz_columnas': problema_data.get('matriz_columnas'),
                        'fichas': problema_data['fichas'],
                        'respuesta': problema_data['respuesta'],
                        'configuracion_extra': configuracion_extra  # Nuevo campo
                    }
                )
                total_problemas += 1
            
            self.stdout.write(self.style.SUCCESS(f'¡{total_problemas} problemas cargados exitosamente!'))
        
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('Archivo problemas_domino.json no encontrado'))
        except KeyError as e:
            self.stdout.write(self.style.ERROR(f'Error en estructura JSON: clave faltante {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error inesperado: {str(e)}'))