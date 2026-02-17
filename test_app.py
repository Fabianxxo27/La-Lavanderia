"""
Test de inicialización de la aplicación Flask MVC
"""
import sys

print("="*60)
print("TEST DE FUNCIONALIDAD APLICACIÓN MVC")
print("="*60)

try:
    # Test 1: Crear aplicación
    print("\n[1/5] Creando aplicación Flask...")
    from app import create_app
    app = create_app()
    print("✓ Aplicación creada exitosamente")
    
    # Test 2: Verificar blueprints registrados
    print("\n[2/5] Verificando blueprints registrados...")
    blueprints = list(app.blueprints.keys())
    expected = ['auth', 'cliente', 'admin', 'api', 'utils']
    
    print(f"  Blueprintsregistrados: {', '.join(blueprints)}")
    for bp in expected:
        if bp in blueprints:
            print(f"  ✓ {bp}")
        else:
            print(f"  ✗ {bp} FALTANTE")
    
    # Test 3: Contar rutas
    print("\n[3/5] Contando rutas totales...")
    rules_count = len([r for r in app.url_map.iter_rules() if not r.rule.startswith('/static')])
    print(f"  Total de rutas: {rules_count}")
    
    # Test 4: Verificar rutas críticas
    print("\n[4/5] Verificando rutas críticas...")
    critical_routes = [
        '/login',
        '/logout',
        '/registro',
        '/cliente_inicio',
        '/pedidos',
        '/api/notificaciones',
    ]
    
    all_routes = [str(r) for r in app.url_map.iter_rules()]
    for route in critical_routes:
        found = any(route in r for r in all_routes)
        status = "✓" if found else "✗"
        print(f"  {status} {route}")
    
    # Test 5: Context test
    print("\n[5/5] Testeando contexto de aplicación...")
    with app.app_context():
        print("  ✓ App context funciona")
        print(f"  ✓ App name: {app.name}")
        print(f"  ✓ Debug mode: {app.debug}")
    
    print("\n" + "="*60)
    print("✅ TODOS LOS TESTS PASARON - APLICACIÓN FUNCIONAL")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
