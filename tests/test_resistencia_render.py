#!/usr/bin/env python
"""
Prueba de resistencia: mantiene carga constante durante tiempo prolongado.
Detecta memory leaks, conexiones no cerradas, drift de performance.

USO:
    python tests/test_resistencia_render.py

Edita DURACION_MINUTOS = 60 para cambiar duración.
"""

import sys
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import os

# Intenta importar requests
try:
    import requests
except ImportError:
    print("ERROR: 'requests' no está instalado")
    print("Ejecuta: pip install requests")
    sys.exit(1)

RENDER_URL = os.getenv("RENDER_URL", "https://la-lavanderia.onrender.com")
DURACION_MINUTOS = 10  # Cambia a 60 para prueba de 1 hora
USUARIOS_SIMULTANEOS = 5

def realizar_operacion(numero_operacion, session=None):
    """Realiza operaciones en la app"""
    if session is None:
        session = requests.Session()
    
    try:
        # Login
        response = session.post(
            f"{RENDER_URL}/login",
            data={"username": "testuser1", "password": "TestPassword123!"},
            timeout=10
        )
        
        if response.status_code != 200:
            return {"exito": False, "error": f"Login falló", "operacion": numero_operacion}
        
        # Realiza varias acciones
        acciones = [
            session.get(f"{RENDER_URL}/cliente_inicio", timeout=10),
            session.get(f"{RENDER_URL}/cliente_pedidos", timeout=10),
            session.get(f"{RENDER_URL}/cliente_promociones", timeout=10),
        ]
        
        return {
            "exito": all(a.status_code == 200 for a in acciones),
            "operacion": numero_operacion,
            "timestamp": datetime.now()
        }
    except Exception as e:
        return {"exito": False, "error": str(e), "operacion": numero_operacion}

def prueba_resistencia():
    """Ejecuta prueba de resistencia por tiempo prolongado"""
    
    print(f"\n{'='*75}")
    print(f"PRUEBA DE RESISTENCIA EN RENDER")
    print(f"URL: {RENDER_URL}")
    print(f"Usuarios simultáneos: {USUARIOS_SIMULTANEOS}")
    print(f"Duración: {DURACION_MINUTOS} minutos")
    print(f"Inicio: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*75}\n")
    
    inicio_total = time.time()
    fin_prueba = inicio_total + (DURACION_MINUTOS * 60)
    
    operacion_num = 0
    exitosas = 0
    fallidas = 0
    reportado_inicio = False
    
    while time.time() < fin_prueba:
        tiempo_iteracion_inicio = time.time()
        
        try:
            with ThreadPoolExecutor(max_workers=USUARIOS_SIMULTANEOS) as executor:
                resultados = list(executor.map(realizar_operacion, range(100, 100 + USUARIOS_SIMULTANEOS)))
            
            # Analiza resultados
            for r in resultados:
                operacion_num += 1
                if r["exito"]:
                    exitosas += 1
                else:
                    fallidas += 1
            
            # Reporte cada minuto
            tiempo_transcurrido = int((time.time() - inicio_total) / 60)
            if tiempo_transcurrido > 0 and not (tiempo_transcurrido % 1) and not reportado_inicio:
                tasa_exito = (exitosas / (exitosas + fallidas) * 100) if (exitosas + fallidas) > 0 else 0
                print(f"[+{tiempo_transcurrido:02d}min] "
                      f"OPs: {operacion_num:>5} | "
                      f"Éxito: {exitosas:>5} | "
                      f"Fallos: {fallidas:>5} | "
                      f"Tasa: {tasa_exito:>5.1f}%")
                reportado_inicio = True
            elif tiempo_transcurrido % 1:
                reportado_inicio = False
        
        except Exception as e:
            print(f"Error en iteración: {e}")
        
        # Control de velocidad
        tiempo_iteracion = time.time() - tiempo_iteracion_inicio
        if tiempo_iteracion < 2:
            time.sleep(2 - tiempo_iteracion)
    
    # Reporte final
    tiempo_total = time.time() - inicio_total
    tasa_exito_final = (exitosas / (exitosas + fallidas) * 100) if (exitosas + fallidas) > 0 else 0
    
    print(f"\n{'='*75}")
    print(f"RESULTADOS FINALES")
    print(f"{'='*75}")
    print(f"Duración: {int(tiempo_total/60)}min {int(tiempo_total%60)}s")
    print(f"Total operaciones: {operacion_num}")
    print(f"Exitosas: {exitosas} ({tasa_exito_final:.2f}%)")
    print(f"Fallidas: {fallidas}")
    print(f"Operaciones por segundo: {operacion_num/tiempo_total:.2f}")
    
    if tasa_exito_final > 95:
        print(f"\n✓ App resistió bien la prueba de carga prolongada")
    else:
        print(f"\n⚠ App tuvo problemas durante el test")
    print(f"{'='*75}\n")

if __name__ == "__main__":
    prueba_resistencia()
