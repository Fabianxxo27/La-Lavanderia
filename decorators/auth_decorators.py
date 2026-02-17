"""
Decoradores de autenticación y autorización
"""
from functools import wraps
from flask import session, flash, redirect, url_for


def login_requerido(f):
    """
    Decorador para rutas que necesitan autenticación.
    Verifica que el usuario haya iniciado sesión.
    
    Args:
        f: función a decorar
        
    Returns:
        función decorada
    """
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'id_usuario' not in session:
            flash('Debes iniciar sesión', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorador


def admin_requerido(f):
    """
    Decorador para rutas de administrador.
    Verifica que el usuario haya iniciado sesión y sea administrador.
    
    Args:
        f: función a decorar
        
    Returns:
        función decorada
    """
    @wraps(f)
    def decorador(*args, **kwargs):
        if 'id_usuario' not in session:
            flash('Debes iniciar sesión', 'warning')
            return redirect(url_for('auth.login'))
        
        rol = str(session.get('rol', '')).strip().lower()
        if rol != 'administrador':
            flash('No tienes permisos para acceder a esta página', 'danger')
            return redirect(url_for('cliente.cliente_inicio'))
        return f(*args, **kwargs)
    return decorador
