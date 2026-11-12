# users/utils.py
"""
Utilidades para la creación rápida de estudiantes desde el panel admin.

- generar_username(full_name, email): genera un username slugificado a partir
  del nombre completo. Si ya existe, le agrega un fragmento del email
  (antes del @) para desambiguar, y si AÚN existe, añade un número.
- generar_password_temporal(): genera una contraseña aleatoria segura,
  legible (sin caracteres ambiguos como 0/O, 1/l/I).
"""
import re
import secrets
import unicodedata

from users.models import CustomUser


def _slugify_simple(texto: str) -> str:
    """
    Convierte 'Juan Pérez López' -> 'juan_perez_lopez'
    Quita acentos, pasa a minúsculas, reemplaza espacios/símbolos por '_'.
    """
    texto = unicodedata.normalize('NFKD', texto)
    texto = texto.encode('ascii', 'ignore').decode('ascii')  # quita acentos
    texto = texto.lower().strip()
    texto = re.sub(r'[^a-z0-9]+', '_', texto)
    texto = re.sub(r'_+', '_', texto).strip('_')
    return texto or 'usuario'


def generar_username(full_name: str, email: str) -> str:
    """
    Genera un username único a partir del nombre completo.
    Estrategia de desambiguación (en este orden):
      1. base                      -> 'juan_perez'
      2. base + fragmento de email -> 'juan_perez_gm' (de 'gmail')
      3. base + fragmento + número -> 'juan_perez_gm2'
    """
    base = _slugify_simple(full_name)[:140]  # margen para sufijos (max_length=150)

    if not CustomUser.objects.filter(username=base).exists():
        return base

    # Fragmento del email antes del @ (ej: 'juanperez99@gmail.com' -> 'gmail' -> 'gm')
    dominio = email.split('@')[-1].split('.')[0] if '@' in email else ''
    fragmento = _slugify_simple(dominio)[:6] if dominio else 'usr'

    candidato = f'{base}_{fragmento}'[:147]
    if not CustomUser.objects.filter(username=candidato).exists():
        return candidato

    # Último recurso: número incremental
    contador = 2
    while True:
        candidato_num = f'{candidato}{contador}'[:150]
        if not CustomUser.objects.filter(username=candidato_num).exists():
            return candidato_num
        contador += 1


_ALFABETO_PASSWORD = (
    'abcdefghjkmnpqrstuvwxyz'   # sin i, l, o (ambiguos)
    'ABCDEFGHJKMNPQRSTUVWXYZ'   # sin I, L, O
    '23456789'                  # sin 0, 1
)


def generar_password_temporal(longitud: int = 11) -> str:
    """
    Genera una contraseña aleatoria, legible (sin caracteres ambiguos),
    suficientemente fuerte para Django's password validators por defecto
    (longitud >= 8, no completamente numérica, no común).
    """
    return ''.join(secrets.choice(_ALFABETO_PASSWORD) for _ in range(longitud))