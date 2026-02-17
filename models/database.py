"""
Configuración de la base de datos y funciones de consulta
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Instancia de SQLAlchemy
db = SQLAlchemy()


def run_query(query, params=None, fetchone=False, fetchall=False, commit=False, get_lastrowid=False):
    """
    Utilidad para ejecutar consultas SQL.

    - Para lecturas: usar fetchone=True o fetchall=True.
    - Para escrituras (commit=True): si get_lastrowid=True la función devuelve el último id insertado (si está disponible).
    
    Args:
        query: consulta SQL con placeholders :param
        params: diccionario de parámetros
        fetchone: devolver una fila
        fetchall: devolver todas las filas
        commit: hacer commit (para INSERT, UPDATE, DELETE)
        get_lastrowid: devolver el último id insertado
        
    Returns:
        - Si fetchone: una fila o None
        - Si fetchall: lista de filas
        - Si get_lastrowid: último id insertado
        - None en otros casos
    """
    if commit:
        # Para INSERT, UPDATE, DELETE
        with db.engine.begin() as conn:  # begin() hace commit al salir del bloque
            result = conn.execute(text(query), params or {})
            
            # Si piden fetchone, devolver la fila
            if fetchone:
                return result.fetchone()
            
            # Si piden fetchall, devolver todas las filas
            if fetchall:
                return result.fetchall()
            
            # Si piden lastrowid, intentar extraerlo
            if get_lastrowid:
                try:
                    return result.lastrowid
                except Exception:
                    return None
            
            return None
    else:
        # Para SELECT
        with db.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            if fetchone:
                return result.fetchone()
            if fetchall:
                return result.fetchall()
            return None


def ensure_cliente_exists(id_usuario):
    """
    Garantiza que existe un registro en la tabla cliente para un usuario.
    Si no existe, lo crea automáticamente.
    
    Args:
        id_usuario: ID del usuario
    """
    try:
        cliente_exists = run_query(
            "SELECT id_cliente FROM cliente WHERE id_cliente = :id",
            {"id": id_usuario},
            fetchone=True
        )
        
        if not cliente_exists:
            # Obtener datos del usuario para crear el cliente
            usuario = run_query(
                "SELECT nombre, email FROM usuario WHERE id_usuario = :id",
                {"id": id_usuario},
                fetchone=True
            )
            
            if usuario:
                run_query(
                    "INSERT INTO cliente (id_cliente, nombre, email) VALUES (:ic, :n, :e)",
                    {
                        "ic": id_usuario,
                        "n": usuario[0],
                        "e": usuario[1]
                    },
                    commit=True
                )
                print(f"✓ Cliente creado automáticamente para id_usuario={id_usuario}")
    except Exception as e:
        print(f"✗ Error en ensure_cliente_exists: {e}")
        raise
