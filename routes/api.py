"""
Blueprint de API
API REST endpoints
"""
from flask import Blueprint, request, session, jsonify
from models import run_query
from decorators import login_requerido, admin_requerido
from helpers import crear_notificacion

bp = Blueprint('api', __name__)


# -----------------------------------------------
# API: OBTENER PRENDAS DE UN PEDIDO (JSON)
# -----------------------------------------------
@bp.route('/api/prendas_pedido/<int:id_pedido>')
def api_prendas_pedido(id_pedido):
    """API para obtener prendas de un pedido en JSON (para cargas dinámicas)."""
    username = session.get('username')
    rol = session.get('rol')
    
    if not username:
        return jsonify({'error': 'No autorizado'}), 401
    
    # Verificar permisos
    pedido = run_query(
        "SELECT id_cliente FROM pedido WHERE id_pedido = :id",
        {"id": id_pedido},
        fetchone=True
    )
    
    if not pedido:
        return jsonify({'error': 'Pedido no encontrado'}), 404
    
    if rol != 'administrador':
        usuario = run_query(
            "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
            {"u": username.lower()},
            fetchone=True
        )
        if usuario[0] != pedido[0]:
            return jsonify({'error': 'Acceso denegado'}), 403
    
    # Obtener prendas con precios calculados según tipo
    prendas_data = run_query("""
        SELECT 
            p.tipo, 
            COUNT(*) as cantidad,
            p.descripcion,
            CASE p.tipo
                WHEN 'Camisa' THEN 5000
                WHEN 'Pantalón' THEN 6000
                WHEN 'Vestido' THEN 8000
                WHEN 'Chaqueta' THEN 10000
                WHEN 'Saco' THEN 7000
                WHEN 'Falda' THEN 5500
                WHEN 'Blusa' THEN 4500
                WHEN 'Abrigo' THEN 12000
                WHEN 'Suéter' THEN 6500
                WHEN 'Jeans' THEN 7000
                WHEN 'Corbata' THEN 3000
                WHEN 'Bufanda' THEN 3500
                WHEN 'Sábana' THEN 8000
                WHEN 'Edredón' THEN 15000
                WHEN 'Cortina' THEN 12000
                ELSE 5000
            END as precio
        FROM prenda p
        WHERE p.id_pedido = :id
        GROUP BY p.tipo, p.descripcion
        ORDER BY p.tipo
    """, {"id": id_pedido}, fetchall=True)
    
    prendas = []
    for prenda in prendas_data:
        prendas.append({
            'tipo': prenda[0],
            'cantidad': int(prenda[1]) if prenda[1] else 0,
            'descripcion': prenda[2] or '',
            'precio': float(prenda[3]) if prenda[3] else 5000
        })
    
    return jsonify({'prendas': prendas})


# -----------------------------------------------
# API: AUTOCOMPLETADO DE CLIENTES
# -----------------------------------------------
@bp.route('/api/autocomplete/clientes')
@login_requerido
@admin_requerido
def api_autocomplete_clientes():
    """API para autocompletado de clientes."""
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify([])
    
    # Buscar clientes que coincidan con el query
    clientes = run_query("""
        SELECT id_usuario, nombre, email, username
        FROM usuario
        WHERE rol = 'cliente' 
        AND (
            LOWER(nombre) LIKE LOWER(:q) OR
            LOWER(email) LIKE LOWER(:q) OR
            LOWER(username) LIKE LOWER(:q) OR
            CAST(id_usuario AS TEXT) LIKE :q
        )
        ORDER BY nombre
        LIMIT 10
    """, {"q": f"%{query}%"}, fetchall=True)
    
    resultados = []
    for cliente in clientes:
        resultados.append({
            'id': cliente[0],
            'nombre': cliente[1],
            'email': cliente[2] or '',
            'username': cliente[3] or '',
            'label': f"{cliente[1]} ({cliente[2] or cliente[3]})"
        })
    
    return jsonify(resultados)


# -----------------------------------------------
# API: AUTOCOMPLETADO DE ESTADOS
# -----------------------------------------------
@bp.route('/api/autocomplete/estados')
@login_requerido
def api_autocomplete_estados():
    """API para autocompletado de estados de pedidos."""
    query = request.args.get('q', '').strip().lower()
    
    # Estados posibles
    todos_estados = ['Pendiente', 'En proceso', 'Completado', 'Cancelado', 'Entregado']
    
    if not query:
        return jsonify(todos_estados)
    
    # Filtrar estados que coincidan
    estados_filtrados = [e for e in todos_estados if query in e.lower()]
    
    return jsonify(estados_filtrados)


# -----------------------------------------------
# API: NOTIFICACIONES
# -----------------------------------------------
@bp.route('/api/notificaciones')
@login_requerido
def api_notificaciones():
    """Obtiene las notificaciones del usuario actual."""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'No autorizado'}), 401
    
    # Obtener id_usuario
    usuario = run_query(
        "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
        {"u": username.lower()},
        fetchone=True
    )
    
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    id_usuario = usuario[0]
    
    # Obtener notificaciones (últimas 20, ordenadas por fecha)
    notificaciones = run_query("""
        SELECT id_notificacion, titulo, mensaje, tipo, leida, url, 
               fecha_creacion
        FROM notificacion
        WHERE id_usuario = :id
        ORDER BY fecha_creacion DESC
        LIMIT 20
    """, {"id": id_usuario}, fetchall=True)
    
    # Convertir a lista de diccionarios
    resultado = []
    for n in notificaciones:
        resultado.append({
            'id_notificacion': n[0],
            'titulo': n[1],
            'mensaje': n[2],
            'tipo': n[3],
            'leida': n[4],
            'url': n[5],
            'fecha_creacion': n[6].isoformat() if n[6] else None
        })
    
    return jsonify(resultado)


@bp.route('/api/notificaciones/no-leidas')
@login_requerido
def api_notificaciones_no_leidas():
    """Cuenta las notificaciones no leídas del usuario actual."""
    username = session.get('username')
    if not username:
        return jsonify({'count': 0})
    
    usuario = run_query(
        "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
        {"u": username.lower()},
        fetchone=True
    )
    
    if not usuario:
        return jsonify({'count': 0})
    
    id_usuario = usuario[0]
    
    count = run_query("""
        SELECT COUNT(*) FROM notificacion
        WHERE id_usuario = :id AND leida = FALSE
    """, {"id": id_usuario}, fetchone=True)[0] or 0
    
    return jsonify({'count': count})


@bp.route('/api/notificaciones/<int:id_notificacion>/marcar-leida', methods=['POST'])
@login_requerido
def api_marcar_notificacion_leida(id_notificacion):
    """Marca una notificación como leída."""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'No autorizado'}), 401
    
    usuario = run_query(
        "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
        {"u": username.lower()},
        fetchone=True
    )
    
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    id_usuario = usuario[0]
    
    # Marcar como leída solo si pertenece al usuario
    run_query("""
        UPDATE notificacion
        SET leida = TRUE
        WHERE id_notificacion = :id AND id_usuario = :id_usuario
    """, {"id": id_notificacion, "id_usuario": id_usuario}, commit=True)
    
    return jsonify({'success': True})


@bp.route('/api/notificaciones/marcar-todas-leidas', methods=['POST'])
@login_requerido
def api_marcar_todas_leidas():
    """Marca todas las notificaciones del usuario como leídas."""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'No autorizado'}), 401
    
    usuario = run_query(
        "SELECT id_usuario FROM usuario WHERE LOWER(username) = :u",
        {"u": username.lower()},
        fetchone=True
    )
    
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    id_usuario = usuario[0]
    
    run_query("""
        UPDATE notificacion
        SET leida = TRUE
        WHERE id_usuario = :id AND leida = FALSE
    """, {"id": id_usuario}, commit=True)
    
    return jsonify({'success': True})
