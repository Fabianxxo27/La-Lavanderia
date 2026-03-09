from pathlib import Path
import re

original = Path('app_original_backup.py').read_text(encoding='utf-8')

mvc_entries = [
    ('routes/auth.py', 'index', 'index'),
    ('routes/auth.py', 'login', 'login'),
    ('routes/auth.py', 'registro', 'registro'),
    ('routes/auth.py', 'logout', 'logout'),

    ('routes/cliente.py', 'cliente_inicio', 'cliente_inicio'),
    ('routes/cliente.py', 'cliente_recibos', 'cliente_recibos'),
    ('routes/cliente.py', 'cliente_promociones', 'cliente_promociones'),
    ('routes/cliente.py', 'cliente_pedidos', 'cliente_pedidos'),

    ('routes/admin.py', 'inicio', 'inicio'),
    ('routes/admin.py', 'pedidos', 'pedidos'),
    ('routes/admin.py', 'calendario_pedidos', 'calendario_pedidos'),
    ('routes/admin.py', 'actualizar_pedido', 'actualizar_pedido'),
    ('routes/admin.py', 'eliminar_pedido', 'eliminar_pedido'),
    ('routes/admin.py', 'pedido_detalles', 'pedido_detalles'),
    ('routes/admin.py', 'clientes', 'clientes'),
    ('routes/admin.py', 'registro_rapido', 'registro_rapido'),
    ('routes/admin.py', 'agregar_cliente', 'agregar_cliente'),
    ('routes/admin.py', 'actualizar_cliente', 'actualizar_cliente'),
    ('routes/admin.py', 'eliminar_cliente', 'eliminar_cliente'),
    ('routes/admin.py', 'terminos_descuentos', 'terminos_descuentos'),
    ('routes/admin.py', 'configurar_descuentos', 'configurar_descuentos'),
    ('routes/admin.py', 'ejecutar_migraciones_admin', 'ejecutar_migraciones_admin'),
    ('routes/admin.py', 'crear_descuento', 'crear_descuento'),
    ('routes/admin.py', 'editar_descuento', 'editar_descuento'),
    ('routes/admin.py', 'eliminar_descuento', 'eliminar_descuento'),
    ('routes/admin.py', 'reportes', 'reportes'),
    ('routes/admin.py', 'reportes_export_excel', 'reportes_export_excel'),
    ('routes/admin.py', 'agregar_pedido', 'agregar_pedido'),

    ('routes/utils.py', 'lector_barcode', 'lector_barcode'),
    ('routes/utils.py', 'ver_prendas_pedido', 'ver_prendas_pedido'),
    ('routes/utils.py', 'generar_barcode', 'generar_barcode'),
    ('routes/utils.py', 'descargar_barcode', 'descargar_barcode'),
    ('routes/utils.py', 'descargar_recibo_pdf', 'descargar_recibo_pdf'),

    ('routes/api.py', 'api_prendas_pedido', 'api_prendas_pedido'),
    ('routes/api.py', 'api_autocomplete_clientes', 'api_autocomplete_clientes'),
    ('routes/api.py', 'api_autocomplete_estados', 'api_autocomplete_estados'),
    ('routes/api.py', 'api_notificaciones', 'api_notificaciones'),
    ('routes/api.py', 'api_notificaciones_no_leidas', 'api_notificaciones_no_leidas'),
    ('routes/api.py', 'api_marcar_notificacion_leida', 'api_marcar_notificacion_leida'),
    ('routes/api.py', 'api_marcar_todas_leidas', 'api_marcar_todas_leidas')
]

helper_map = {
    'admin_only': '_admin_only',
    'tabla_descuento_existe': '_tabla_descuento_existe',
    'ejecutar_sql_file': '_ejecutar_sql_file',
    'get_safe_redirect': '_get_safe_redirect',
    'obtener_esquema_descuento_cliente': '_obtener_esquema_descuento_cliente'
}


def extract_func(text, name):
    pattern = re.compile(r"^def %s\(.*?\):" % re.escape(name), re.M)
    match = pattern.search(text)
    if not match:
        return None
    start = match.start()
    rest = text[start:]
    next_block = re.search(r"^(@|def )", rest[1:], re.M)
    end = start + (next_block.start() if next_block else len(rest))
    return text[start:end]


def normalize(text):
    if text is None:
        return None
    text = re.sub(r"(?ms)^\s*\"\"\"[\s\S]*?\"\"\"\s*$", "", text)
    text = re.sub(r"(?ms)^\s*'''[\s\S]*?'''\s*$", "", text)
    text = re.sub(r"url_for\(\"([^\"]+)\"\)", r"url_for('\1')", text)
    text = re.sub(r"url_for\('\s*(auth|admin|cliente|utils)\.", "url_for('", text)
    for new, old in helper_map.items():
        text = text.replace(new, old)
    text = text.replace('__admin_only', '_admin_only')
    text = text.replace('__tabla_descuento_existe', '_tabla_descuento_existe')
    text = text.replace('__ejecutar_sql_file', '_ejecutar_sql_file')
    text = text.replace('__get_safe_redirect', '_get_safe_redirect')
    text = text.replace('__obtener_esquema_descuento_cliente', '_obtener_esquema_descuento_cliente')
    lines = [line.rstrip() for line in text.splitlines() if line.strip() != '' and not line.strip().startswith('#')]
    return "\n".join(lines)


mismatches = []
missing = []

for file_path, mvc_name, original_name in mvc_entries:
    mvc_text = Path(file_path).read_text(encoding='utf-8')
    orig_block = extract_func(original, original_name)
    mvc_block = extract_func(mvc_text, mvc_name)
    if orig_block is None or mvc_block is None:
        missing.append((file_path, mvc_name, original_name, orig_block is None, mvc_block is None))
        continue
    if normalize(orig_block) != normalize(mvc_block):
        mismatches.append((file_path, mvc_name, original_name))

print('MISSING FUNCTIONS:', len(missing))
for item in missing:
    print(' -', item)
print('MISMATCHED FUNCTIONS:', len(mismatches))
for item in mismatches:
    print(' -', item[0], item[1], '(original:', item[2] + ')')

if not missing and not mismatches:
    print('OK: All compared functions match original (after normalization).')
