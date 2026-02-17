"""
Módulo de modelos y base de datos
"""
from .database import db, run_query, ensure_cliente_exists

__all__ = ['db', 'run_query', 'ensure_cliente_exists']
