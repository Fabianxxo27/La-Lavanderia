from pathlib import Path

mapping = {
    # auth
    'index': 'auth.index',
    'login': 'auth.login',
    'registro': 'auth.registro',
    'logout': 'auth.logout',
    # admin
    'inicio': 'admin.inicio',
    'pedidos': 'admin.pedidos',
    'clientes': 'admin.clientes',
    'agregar_cliente': 'admin.agregar_cliente',
    'actualizar_cliente': 'admin.actualizar_cliente',
    'eliminar_cliente': 'admin.eliminar_cliente',
    'agregar_pedido': 'admin.agregar_pedido',
    'pedido_detalles': 'admin.pedido_detalles',
    'actualizar_pedido': 'admin.actualizar_pedido',
    'eliminar_pedido': 'admin.eliminar_pedido',
    'terminos_descuentos': 'admin.terminos_descuentos',
    'configurar_descuentos': 'admin.configurar_descuentos',
    'ejecutar_migraciones_admin': 'admin.ejecutar_migraciones_admin',
    'crear_descuento': 'admin.crear_descuento',
    'editar_descuento': 'admin.editar_descuento',
    'eliminar_descuento': 'admin.eliminar_descuento',
    'reportes': 'admin.reportes',
    'reportes_export_excel': 'admin.reportes_export_excel',
    'calendario_pedidos': 'admin.calendario_pedidos',
    # cliente
    'cliente_inicio': 'cliente.cliente_inicio',
    'cliente_pedidos': 'cliente.cliente_pedidos',
    'cliente_recibos': 'cliente.cliente_recibos',
    'cliente_promociones': 'cliente.cliente_promociones',
    # utils
    'lector_barcode': 'utils.lector_barcode',
    'descargar_recibo_pdf': 'utils.descargar_recibo_pdf',
    'descargar_barcode': 'utils.descargar_barcode',
    'pedido_prendas': 'utils.pedido_prendas',
    'generar_recibo': 'utils.generar_recibo',
    'generar_barcode': 'utils.generar_barcode',
}

root = Path('templates')
files = list(root.rglob('*.html'))

changed = []
for path in files:
    content = path.read_text(encoding='utf-8')
    original = content
    for old, new in mapping.items():
        content = content.replace("url_for('%s')" % old, "url_for('%s')" % new)
        content = content.replace('url_for("%s")' % old, 'url_for("%s")' % new)
        content = content.replace("url_for('%s'," % old, "url_for('%s'," % new)
        content = content.replace('url_for("%s",' % old, 'url_for("%s",' % new)
    if content != original:
        path.write_text(content, encoding='utf-8')
        changed.append(str(path))

print('Updated %d template files' % len(changed))
for p in changed:
    print(' - %s' % p)
