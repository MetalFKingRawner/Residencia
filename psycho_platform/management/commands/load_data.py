import json
from django.core.management.base import BaseCommand
from core.models import Proyecto, Lote, Propietario, Vendedor

class Command(BaseCommand):
    help = 'Carga datos iniciales desde JSON'
    
    def handle(self, *args, **options):
        with open('datos.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Crear proyectos
        proyectos_map = {}
        for proyecto_data in data['proyectos']:
            proyecto = Proyecto.objects.create(
                id=proyecto_data['id'],
                nombre=proyecto_data['nombre'],
                tipo_contrato=proyecto_data['tipo_contrato'],
                ubicacion=proyecto_data['ubicacion']
            )
            proyectos_map[proyecto.id] = proyecto
        
        # Crear lotes
        for lote_data in data['lotes']:
            Lote.objects.create(
                proyecto_id=lote_data['proyecto_id'],
                identificador=lote_data['identificador'],
                norte=lote_data['norte'],
                sur=lote_data['sur'],
                este=lote_data.get('este', ''),  # Usar get() para campos opcionales
                oeste=lote_data.get('oeste', ''),
                manzana=lote_data.get('manzana')
            )
        
        # Crear propietarios
        for prop_data in data['propietarios']:
            Propietario.objects.create(
                proyecto_id=prop_data['proyecto_id'],
                nombre_completo=prop_data['nombre_completo'],
                nacionalidad=prop_data['nacionalidad'],
                domicilio=prop_data['domicilio'],
                ine=prop_data['ine'],
                telefono=prop_data['telefono'],
                email=prop_data['email'],
                tipo=prop_data['tipo'],
                instrumento_publico=prop_data.get('instrumento_publico'),
                notario_publico=prop_data.get('notario_publico'),
                nombre_notario=prop_data.get('nombre_notario')
            )
        
        # Crear vendedores y relaciones
        for vend_data in data['vendedores']:
            vendedor, created = Vendedor.objects.get_or_create(
                ine=vend_data['ine'],
                defaults={
                    'nombre_completo': vend_data['nombre_completo'],
                    'nacionalidad': vend_data['nacionalidad'],
                    'domicilio': vend_data['domicilio'],
                    'telefono': vend_data['telefono'],
                    'email': vend_data['email'],
                    'tipo': vend_data['tipo']
                }
            )
            # Añadir relaciones con proyectos
            for proyecto_id in vend_data['proyectos']:
                proyecto = Proyecto.objects.get(id=proyecto_id)
                vendedor.proyectos.add(proyecto)
        
        self.stdout.write(self.style.SUCCESS('Datos cargados exitosamente'))