"""
Pruebas de carga contra la aplicación en Render.
Se simula múltiples usuarios navegando la app en la nube.

⚠️  NO EJECUTES ESTE ARCHIVO DIRECTAMENTE
Usa en su lugar: locust -f tests/locustfile_render.py

INSTALACIÓN:
    pip install locust

USO:
    locust -f tests/locustfile_render.py --users 20 --spawn-rate 2 --run-time 5m
    Abre: http://localhost:8089

O sin interfaz:
    locust -f tests/locustfile_render.py --headless --users 20 --spawn-rate 2 --run-time 5m
"""

import sys
import os

# Fuerza desactivación de SSL a nivel de entorno ANTES de importar locust
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['CURL_CA_BUNDLE'] = ''

# Validar que se ejecuta con locust, no directamente
if __name__ == "__main__":
    print("❌ ERROR: No ejecutes este archivo directamente")
    print("")
    print("Este es un archivo de configuración para Locust.")
    print("Debes ejecutarlo así:")
    print("")
    print("  locust -f tests/locustfile_render.py --users 20 --spawn-rate 2")
    print("")
    print("O desde la raíz del proyecto:")
    print("")
    print("  locust -f tests/locustfile_render.py --users 20")
    sys.exit(1)

import warnings
from datetime import datetime

# Deshabilita verificación de SSL globalmente
import urllib3
urllib3.disable_warnings()

# Monkeypatch SSL
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

warnings.filterwarnings('ignore')

# Verifica que locust esté instalado
try:
    from locust import HttpUser, task, between, TaskSet
    from locust.clients import HttpSession
except ImportError:
    print("ERROR: 'locust' no está instalado")
    print("Ejecuta: pip install locust")
    sys.exit(1)

# Crea cliente personalizado que ignora SSL
class HttpUserNoSSL(HttpUser):
    """HttpUser que ignora errores de verificación SSL"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Deshabilita verificación en cada sesión
        self.client.verify = False

# REEMPLAZA CON TU URL DE RENDER
RENDER_URL = os.getenv("RENDER_URL", "https://la-lavanderia.onrender.com")

print(f"\n{'='*70}")
print(f"PRUEBAS DE CARGA - RENDER")
print(f"URL: {RENDER_URL}")
print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*70}\n")


class ClienteRenderUser(HttpUserNoSSL):
    """Simula un cliente usando la app en Render"""
    
    wait_time = between(1, 3)
    weight = 8  # 8 clientes por cada 2 admins
    
    def on_start(self):
        """Login inicial"""
        try:
            response = self.client.post(
                f"{RENDER_URL}/login",
                data={
                    "username": "testuser1",
                    "password": "TestPassword123!"
                },
                timeout=20
            )
        except Exception as e:
            self.environment.events.request.fire(
                request_type="POST", name="/login", response_time=-1,
                response_length=0, exception=e, context={}
            )
    
    @task(4)
    def homepage(self):
        """Visitar página principal"""
        self.client.get(f"{RENDER_URL}/", name="/")
    
    @task(3)
    def ver_pedidos(self):
        """Ver pedidos del cliente"""
        self.client.get(f"{RENDER_URL}/cliente_pedidos", name="/cliente_pedidos")
    
    @task(2)
    def ver_descuentos(self):
        """Ver descuentos y promociones"""
        self.client.get(f"{RENDER_URL}/cliente_promociones", name="/cliente_promociones")
    
    @task(1)
    def ver_recibos(self):
        """Ver recibos"""
        self.client.get(f"{RENDER_URL}/cliente_recibos", name="/cliente_recibos")


class AdminRenderUser(HttpUserNoSSL):
    """Simula un administrador usando la app en Render"""
    
    wait_time = between(2, 5)
    weight = 2  # 2 admins por cada 8 clientes
    
    def on_start(self):
        """Login como admin"""
        try:
            response = self.client.post(
                f"{RENDER_URL}/login",
                data={
                    "username": "admin",
                    "password": "admin_password"
                },
                timeout=20
            )
        except Exception as e:
            self.environment.events.request.fire(
                request_type="POST", name="/login_admin", response_time=-1,
                response_length=0, exception=e, context={}
            )
    
    @task(3)
    def panel_admin(self):
        """Acceder a panel de admin"""
        self.client.get(f"{RENDER_URL}/admin/inicio", name="/admin/inicio")
    
    @task(2)
    def listar_clientes(self):
        """Listar clientes"""
        self.client.get(f"{RENDER_URL}/admin/clientes", name="/admin/clientes")
    
    @task(2)
    def listar_pedidos(self):
        """Listar todos los pedidos"""
        self.client.get(f"{RENDER_URL}/admin/pedidos", name="/admin/pedidos")
    
    @task(1)
    def generar_reporte(self):
        """Generar reporte - operación pesada"""
        self.client.get(f"{RENDER_URL}/admin/reportes_export_excel", 
                       name="/admin/reportes_export_excel", timeout=60)
