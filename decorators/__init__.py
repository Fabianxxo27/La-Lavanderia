"""
Módulo de decoradores
"""
from .auth_decorators import login_requerido, admin_requerido

__all__ = ['login_requerido', 'admin_requerido']
