#!/usr/bin/env python
"""
Prueba de carga usando requests directamente (sin Locust).
Evita completamente los problemas de SSL de geventhttpclient.

USO:
    python tests/test_carga_requests.py
"""

import sys
import os
import warnings
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from urllib3.exceptions import InsecureRequestWarning

# Deshabilita advertencias de SSL
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

RENDER_URL = os.getenv("RENDER_URL", "https://la-lavanderia.onrender.com")
USUARIOS_SIMULTANEOS = 10
DURACION_SEGUNDOS = 120  # 2 minutos

print(f"\n{'='*75}")
print(f"PRUEBA DE CARGA - RENDER (Con Requests, sin Locust)")
print(f"URL: {RENDER_URL}")
print(f"Usuarios simultáneos: {USUARIOS_SIMULTANEOS}")
print(f"Duración: {DURACION_SEGUNDOS}s")
print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*75}\n")

# Estadísticas
stats = {
    "exitosas": 0,
    "fallidas": 0,
    "ssl_errors": 0,
    "timeout_errors": 0,
    "connection_errors": 0,
    "otras_errores": 0,
    "tiempos": []
}

# Rutas a probar
RUTAS = [
    ("/", "GET", {}),
    ("/login", "POST", {"username": "testuser1", "password": "TestPassword123!"}),
    ("/cliente_inicio", "GET", {}),
    ("/cliente_pedidos", "GET", {}),
    ("/cliente_promociones", "GET", {}),
    ("/cliente_recibos", "GET", {}),
    ("/admin/inicio", "GET", {}),
    ("/admin/clientes", "GET", {}),
    ("/admin/pedidos", "GET", {}),
]

def hacer_request(ruta, metodo="GET", datos=None):
    """Realiza un request HTTP con verify=False"""
    try:
        url = f"{RENDER_URL}{ruta}"
        
        if metodo == "GET":
            response = requests.get(url, timeout=20, verify=False, allow_redirects=True)
        elif metodo == "POST":
            response = requests.post(url, data=datos, timeout=20, verify=False, allow_redirects=True)
        
        if response.status_code in [200, 302, 303, 307]:
            return {"exito": True, "tiempo": response.elapsed.total_seconds(), "ruta": ruta}
        else:
            return {"exito": False, "error": f"Status {response.status_code}", "ruta": ruta}
    
    except requests.exceptions.ConnectTimeout:
        return {"exito": False, "error": "ConnectTimeout", "ruta": ruta, "tipo": "timeout"}
    except requests.exceptions.ReadTimeout:
        return {"exito": False, "error": "ReadTimeout", "ruta": ruta, "tipo": "timeout"}
    except requests.exceptions.ConnectionError as e:
        return {"exito": False, "error": "ConnectionError", "ruta": ruta, "tipo": "connection"}
    except requests.exceptions.SSLError as e:
        return {"exito": False, "error": "SSLError", "ruta": ruta, "tipo": "ssl"}
    except Exception as e:
        return {"exito": False, "error": str(e), "ruta": ruta, "tipo": "otro"}

def prueba_carga():
    """Ejecuta la prueba de carga"""
    
    inicio = time.time()
    fin = inicio + DURACION_SEGUNDOS
    numero_request = 0
    
    with ThreadPoolExecutor(max_workers=USUARIOS_SIMULTANEOS) as executor:
        futures = {}
        
        # Inicia requests
        while time.time() < fin:
            for ruta, metodo, datos in RUTAS:
                numero_request += 1
                future = executor.submit(hacer_request, ruta, metodo, datos)
                futures[future] = (ruta, numero_request)
                
                # Evita saturar el thread pool
                if len(futures) >= USUARIOS_SIMULTANEOS * 10:
                    break
            
            # Procesa resultados conforme terminan
            done, futures_restantes = {}, {}
            for future in list(futures.keys()):
                if future.done():
                    ruta, req_num = futures[future]
                    try:
                        resultado = future.result()
                        
                        if resultado["exito"]:
                            stats["exitosas"] += 1
                            stats["tiempos"].append(resultado["tiempo"])
                        else:
                            stats["fallidas"] += 1
                            
                            if resultado.get("tipo") == "ssl":
                                stats["ssl_errors"] += 1
                            elif resultado.get("tipo") == "timeout":
                                stats["timeout_errors"] += 1
                            elif resultado.get("tipo") == "connection":
                                stats["connection_errors"] += 1
                            else:
                                stats["otras_errores"] += 1
                        
                        # Muestra progreso cada 50 requests
                        if (stats["exitosas"] + stats["fallidas"]) % 50 == 0:
                            tasa = stats["exitosas"] / (stats["exitosas"] + stats["fallidas"]) * 100
                            print(f"[+{int(time.time()-inicio):02d}s] "
                                  f"Requests: {stats['exitosas'] + stats['fallidas']:>4} | "
                                  f"Éxito: {stats['exitosas']:>3} | "
                                  f"Fallos: {stats['fallidas']:>3} | "
                                  f"Tasa: {tasa:>5.1f}%")
                    
                    except Exception as e:
                        stats["fallidas"] += 1
                    
                    del futures[future]
                else:
                    futures_restantes[future] = futures[future]
            
            futures = futures_restantes
            
            # Pequeña pausa para no saturar
            time.sleep(0.1)
        
        # Espera a que terminen los requests restantes
        for future in as_completed(futures):
            ruta, req_num = futures[future]
            try:
                resultado = future.result()
                if resultado["exito"]:
                    stats["exitosas"] += 1
                    stats["tiempos"].append(resultado["tiempo"])
                else:
                    stats["fallidas"] += 1
            except:
                stats["fallidas"] += 1
    
    return time.time() - inicio

# Ejecuta la prueba
tiempo_total = prueba_carga()

# Reporte final
print(f"\n{'='*75}")
print(f"RESULTADOS FINALES")
print(f"{'='*75}")
print(f"Tiempo total: {tiempo_total:.1f}s")
print(f"Requests exitosos: {stats['exitosas']}")
print(f"Requests fallidos: {stats['fallidas']}")
print(f"  - SSL Errors: {stats['ssl_errors']}")
print(f"  - Timeout Errors: {stats['timeout_errors']}")
print(f"  - Connection Errors: {stats['connection_errors']}")
print(f"  - Otros Errors: {stats['otras_errores']}")

total = stats['exitosas'] + stats['fallidas']
if total > 0:
    tasa_exito = stats['exitosas'] / total * 100
    requests_por_segundo = total / tiempo_total
    
    print(f"\nTasa de éxito: {tasa_exito:.1f}%")
    print(f"Requests por segundo: {requests_por_segundo:.2f}")
    
    if stats['tiempos']:
        import statistics
        print(f"\nTiempos de respuesta:")
        print(f"  Promedio: {statistics.mean(stats['tiempos'])*1000:.0f}ms")
        print(f"  Mínimo: {min(stats['tiempos'])*1000:.0f}ms")
        print(f"  Máximo: {max(stats['tiempos'])*1000:.0f}ms")
        print(f"  Mediana: {statistics.median(stats['tiempos'])*1000:.0f}ms")

print(f"{'='*75}\n")

# Resultado final
if tasa_exito > 90:
    print("✓ Prueba exitosa: App aguanta bien la carga")
elif tasa_exito > 70:
    print("⚠ Prueba aceptable: App tiene algunos problemas bajo carga")
else:
    print("✗ Prueba falló: App tiene muchos problemas bajo carga")
