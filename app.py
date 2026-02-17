"""
Aplicación Flask - La Lavandería
Punto de entrada principal usando patrón Factory MVC
"""
import datetime
from flask import Flask
from config import Config
from models import db


def create_app(config_class=Config):
    """
    Factory para crear la aplicación Flask.
    
    Args:
        config_class: clase de configuración a usar
        
    Returns:
        instancia de Flask configurada
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Inicializar extensiones
    db.init_app(app)
    
    # Hacer disponible la función now() en todos los templates
    app.jinja_env.globals['now'] = datetime.datetime.now
    
    # Registrar blueprints
    from routes.auth import bp as auth_bp
    from routes.cliente import bp as cliente_bp
    from routes.admin import bp as admin_bp
    from routes.api import bp as api_bp
    from routes.utils import bp as utils_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(cliente_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(utils_bp)
    
    # Error handlers
    @app.after_request
    def agregar_headers_seguridad(response):
        """Agregar headers de seguridad básicos"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    @app.errorhandler(404)
    def pagina_no_encontrada(e):
        """Página 404 personalizada"""
        from flask import render_template
        return render_template('404.html'), 404 if False else ('<h1>404 - Página no encontrada</h1>', 404)

    @app.errorhandler(500)
    def error_servidor(e):
        """Manejo de errores 500"""
        from flask import render_template
        import traceback
        print(f"[ERROR 500] {e}")
        traceback.print_exc()
        return render_template('500.html'), 500 if False else ('<h1>500 - Error del servidor</h1>', 500)
    
    return app


# Crear instancia de la aplicación
app = create_app()


if __name__ == '__main__':
    import os
    # Solo usar desarrollo local si está explícitamente configurado
    # En Render/producción: usar waitress-serve en lugar de app.run()
    environment = os.environ.get('ENV', 'development').lower()
    
    if environment == 'production':
        # En producción (Render), no ejecutar app.run()
        # El Procfile/render.yaml manejará el startup con waitress
        print("✓ Producción detectada. Use: waitress-serve --listen=0.0.0.0:$PORT app:app")
    else:
        # Desarrollo local
        debug_mode = environment == 'development'
        print(f"🚀 Desarrollo local: debug={debug_mode}")
        app.run(host='127.0.0.1', port=5000, debug=debug_mode)
