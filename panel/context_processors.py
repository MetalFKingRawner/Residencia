# panel/context_processors.py

def panel_roles(request):
    """
    Inyecta las variables de roles globalmente en todos los templates.
    Así el base_panel.html siempre sabrá qué mostrar en el menú.
    """
    # Si el usuario no ha iniciado sesión, no devolvemos nada para evitar errores
    if not request.user.is_authenticated:
        return {}

    # Calculamos los roles individuales
    es_sistema = request.user.is_staff  # Administrador del Sistema (soporte técnico)
    es_directivo = request.user.groups.filter(name='Directivo / Coordinador').exists()
    es_instructor = request.user.groups.filter(name='Instructores').exists()

    # 'es_admin' se mantiene por compatibilidad con templates existentes que ya lo usan
    # (equivale a "tiene llave maestra": sistema o directivo)
    es_admin = es_sistema or es_directivo

    # Todo lo que devuelvas en este diccionario estará disponible en TODOS tus HTML
    return {
        'es_sistema': es_sistema,
        'es_directivo': es_directivo,
        'es_instructor': es_instructor,
        'es_admin': es_admin,
    }