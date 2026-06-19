# tests/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    # Si es un diccionario, devuelve el valor
    if isinstance(dictionary, dict):
        return dictionary.get(key, {})
    # Si no es un diccionario, devuelve un diccionario vacío
    return {}
