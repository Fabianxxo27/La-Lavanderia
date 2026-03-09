"""
Blueprint de WhatsApp Bot
Bot básico para respuestas automáticas a clientes via Twilio WhatsApp API
"""
from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
from models import run_query

bp = Blueprint('whatsapp', __name__)


def buscar_pedido_por_id(id_pedido):
    """Busca un pedido por su ID y retorna información formateada."""
    try:
        pedido = run_query("""
            SELECT p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado, c.nombre
            FROM pedido p
            LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
            WHERE p.id_pedido = :id
        """, {"id": id_pedido}, fetchone=True)
        if pedido:
            return (
                f"📋 *Pedido #{pedido[0]}*\n"
                f"👤 Cliente: {pedido[4] or 'N/A'}\n"
                f"📅 Ingreso: {pedido[1]}\n"
                f"📅 Entrega: {pedido[2] or 'Por definir'}\n"
                f"📌 Estado: {pedido[3]}"
            )
        return None
    except Exception:
        return None


def buscar_pedido_por_codigo(codigo):
    """Busca un pedido por código de barras."""
    try:
        pedido = run_query("""
            SELECT p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado, c.nombre
            FROM pedido p
            LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
            WHERE p.codigo_barras = :codigo
        """, {"codigo": codigo}, fetchone=True)
        if pedido:
            return (
                f"📋 *Pedido #{pedido[0]}*\n"
                f"👤 Cliente: {pedido[4] or 'N/A'}\n"
                f"📅 Ingreso: {pedido[1]}\n"
                f"📅 Entrega: {pedido[2] or 'Por definir'}\n"
                f"📌 Estado: {pedido[3]}"
            )
        return None
    except Exception:
        return None


def buscar_pedidos_por_usuario(username):
    """Busca los pedidos de un cliente por su nombre de usuario."""
    try:
        pedidos = run_query("""
            SELECT p.id_pedido, p.fecha_ingreso, p.fecha_entrega, p.estado, c.nombre
            FROM pedido p
            LEFT JOIN cliente c ON p.id_cliente = c.id_cliente
            LEFT JOIN usuario u ON c.id_cliente = u.id_usuario
            WHERE LOWER(u.username) = :username
            ORDER BY p.fecha_ingreso DESC
            LIMIT 5
        """, {"username": username.lower()}, fetchall=True)
        if pedidos:
            resultado = f"📋 *Pedidos de {username}* (últimos 5):\n\n"
            for p in pedidos:
                resultado += (
                    f"▪️ *Pedido #{p[0]}*\n"
                    f"   📅 Ingreso: {p[1]}\n"
                    f"   📅 Entrega: {p[2] or 'Por definir'}\n"
                    f"   📌 Estado: {p[3]}\n\n"
                )
            return resultado.strip()
        return None
    except Exception:
        return None


def obtener_precios():
    """Retorna la lista de precios."""
    return (
        "💰 *Lista de Precios*\n\n"
        "👔 Camisa - $5,000\n"
        "👖 Pantalón - $6,000\n"
        "👗 Vestido - $8,000\n"
        "🧥 Chaqueta - $10,000\n"
        "🧥 Saco - $7,000\n"
        "👗 Falda - $5,500\n"
        "👚 Blusa - $4,500\n"
        "🧥 Abrigo - $12,000\n"
        "🧶 Suéter - $6,500\n"
        "👖 Jeans - $7,000\n"
        "👔 Corbata - $3,000\n"
        "🧣 Bufanda - $3,500\n"
        "🛏️ Sábana - $8,000\n"
        "🛏️ Edredón - $15,000\n"
        "🪟 Cortina - $12,000"
    )


def obtener_horario():
    """Retorna información de horarios."""
    return (
        "🕐 *Horario de Atención*\n\n"
        "Lunes a Viernes: 8:00 AM - 6:00 PM\n"
        "Sábados: 9:00 AM - 2:00 PM\n"
        "Domingos y festivos: Cerrado"
    )


def obtener_menu():
    """Retorna el menú principal del bot."""
    return (
        "🧺 *¡Bienvenido a La Lavandería!*\n\n"
        "¿En qué puedo ayudarte? Escribe una opción:\n\n"
        "1️⃣ *Precios* - Ver lista de precios\n"
        "2️⃣ *Consultar pedido* - Estado de tu pedido\n"
        "3️⃣ *Horario* - Horarios de atención\n"
        "4️⃣ *Ubicación* - ¿Dónde estamos?\n"
        "5️⃣ *Hablar con alguien* - Contactar a un asesor\n\n"
        "También puedes escribir directamente:\n"
        "• _\"pedido 123\"_ para consultar por número\n"
        "• _\"usuario juan123\"_ para ver tus pedidos\n"
        "• _\"precios\"_ para ver la lista de precios"
    )


def procesar_mensaje(mensaje):
    """Procesa el mensaje del usuario y retorna la respuesta apropiada."""
    texto = mensaje.strip().lower()

    # Saludos
    if texto in ('hola', 'hi', 'buenos dias', 'buenas tardes', 'buenas noches', 'hey', 'menu', 'menú', 'inicio'):
        return obtener_menu()

    # Precios
    if texto in ('1', 'precios', 'precio', 'lista de precios', 'cuanto cuesta', 'tarifas'):
        return obtener_precios()

    # Consulta de pedido
    if texto in ('2', 'consultar pedido', 'mi pedido', 'estado pedido', 'pedido'):
        return (
            "🔍 Puedes consultar de dos formas:\n\n"
            "• *pedido 123* - buscar por número de pedido\n"
            "• *usuario juan123* - ver pedidos por tu nombre de usuario"
        )

    # Consulta de pedido con número
    if texto.startswith('pedido '):
        identificador = texto.replace('pedido ', '').strip()
        # Intentar como ID numérico
        if identificador.isdigit():
            resultado = buscar_pedido_por_id(int(identificador))
            if resultado:
                return resultado
        # Intentar como código de barras
        resultado = buscar_pedido_por_codigo(identificador)
        if resultado:
            return resultado
        return "❌ No encontré ningún pedido con ese número. Verifica e intenta de nuevo."

    # Consulta de pedidos por nombre de usuario
    if texto.startswith('usuario '):
        username = texto.replace('usuario ', '').strip()
        if username:
            resultado = buscar_pedidos_por_usuario(username)
            if resultado:
                return resultado
            return f"❌ No encontré pedidos para el usuario *{username}*. Verifica tu nombre de usuario."
        return "⚠️ Por favor escribe tu nombre de usuario.\nEjemplo: *usuario juan123*"

    # Horario
    if texto in ('3', 'horario', 'horarios', 'a que hora abren', 'hora'):
        return obtener_horario()

    # Ubicación
    if texto in ('4', 'ubicacion', 'ubicación', 'donde estan', 'dirección', 'direccion'):
        return (
            "📍 *Nuestra Ubicación*\n\n"
            "Estamos ubicados en:\n"
            "[Tu dirección aquí]\n\n"
            "¡Te esperamos!"
        )

    # Hablar con alguien
    if texto in ('5', 'hablar', 'asesor', 'humano', 'persona', 'ayuda'):
        return (
            "👤 *Contacto Directo*\n\n"
            "Un asesor te atenderá pronto.\n"
            "También puedes llamarnos al:\n"
            "📞 311 531 8569\n\n"
            "Horario de atención:\n"
            "Lunes a Viernes: 8:00 AM - 6:00 PM"
        )

    # Agradecimientos
    if texto in ('gracias', 'thanks', 'ok', 'listo'):
        return "😊 ¡Con gusto! Si necesitas algo más, escribe *menu*."

    # Mensaje no reconocido
    return (
        "🤔 No entendí tu mensaje.\n\n"
        "Escribe *menu* para ver las opciones disponibles,\n"
        "o *pedido 123* para consultar un pedido,\n"
        "o *usuario juan123* para ver tus pedidos."
    )


@bp.route('/whatsapp/webhook', methods=['POST'])
def webhook():
    """Endpoint que recibe mensajes de Twilio WhatsApp."""
    mensaje_entrante = request.values.get('Body', '').strip()
    respuesta = MessagingResponse()
    msg = respuesta.message()
    msg.body(procesar_mensaje(mensaje_entrante))
    return str(respuesta)
