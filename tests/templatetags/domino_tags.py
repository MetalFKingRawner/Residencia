from django import template

register = template.Library()

@register.filter
def times(number):
    """Crea un rango de números para iterar"""
    try:
        return range(1, int(number) + 1)
    except (TypeError, ValueError):
        return range(0)