"""
Servicio de validación y sanitización de datos
"""
import re


def limpiar_texto(texto, max_length=500):
    """
    Limpiar entrada de texto para prevenir XSS.
    
    Args:
        texto: texto a limpiar
        max_length: longitud máxima permitida
        
    Returns:
        texto limpio y seguro
    """
    if not texto:
        return ""
    # Eliminar caracteres peligrosos
    texto = str(texto).strip()
    # Eliminar etiquetas HTML básicas
    texto = re.sub(r'<[^>]+>', '', texto)
    # Limitar longitud
    return texto[:max_length]


def validar_email(email):
    """
    Validar formato de email.
    
    Args:
        email: email a validar
        
    Returns:
        True si el formato es válido, False en caso contrario
    """
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(patron, email))


def validar_contrasena(password):
    """
    Validar que la contraseña sea fuerte.
    
    Args:
        password: contraseña a validar
        
    Returns:
        Tupla (es_valida, mensaje_error)
    """
    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres"
    if not re.search(r'[A-Za-z]', password):
        return False, "La contraseña debe contener letras"
    if not re.search(r'\d', password):
        return False, "La contraseña debe contener números"
    return True, ""
