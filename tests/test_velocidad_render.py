#!/usr/bin/env python
"""
Prueba velocidad de respuesta de cada ruta en Render.
Mide cuánto tarda cada página en responder.

USO:
    python tests/test_velocidad_render.py
"""

import sys
import time
from datetime import datetime
import statistics
import os

# Intenta importar requests, si no está instalado, avisa
try:
    import requests
except ImportError:
    print("ERROR: 'requests' no está instalado")
    print("Ejecuta: pip install requests")
    sys.exit(1)

RENDER_URL = os.getenv("RENDER_URL", "https://la-lavanderia.onrender.com")

RUTAS = {
    "Homepage": "/",
    "Login": "/login",
    "Cliente Inicio": "/cliente_inicio",
    "Mis Pedidos": "/cliente_pedidos",
    "Promociones": "/cliente_promociones",
    "Recibos": "/cliente_recibos",
    "Admin Inicio": "/admin/inicio",
    "Clientes": "/admin/clientes",
    "Pedidos Admin": "/admin/pedidos",
    "Reportes": "/admin/reportes",
}

def medir_velocidad_ruta(ruta, nombre_ruta, repeticiones=3):
    """Mide velocidad de una ruta múltiples veces"""
    
    tiempos = []
    errores = 0
    
    for i in range(repeticiones):
        try:
            inicio = time.time()
            response = requests.get(
                f"{RENDER_URL}{ruta}",
                timeout=30,
                allow_redirects=True
            )
            tiempo = time.time() - inicio
            tiempos.append(tiempo)
            
        except requests.exceptions.Timeout:
            errores += 1
        except Exception as e:
            errores += 1
    
    if tiempos:
        return {
            "nombre": nombre_ruta,
            "ruta": ruta,
            "promedio": statistics.mean(tiempos),
            "min": min(tiempos),
            "max": max(tiempos),
            "mediana": statistics.median(tiempos),
            "errores": errores,
            "exitosas": len(tiempos)
        }
    else:
        return {
            "nombre": nombre_ruta,
            "ruta": ruta,
            "promedio": None,
            "min": None,
            "max": None,
            "errores": errores,
            "exitosas": 0
        }

def test_velocidad():
    """Mide velocidad de todas las rutas"""
    
    print(f"\n{'='*85}")
    print(f"PRUEBA DE VELOCIDAD EN RENDER")
    print(f"URL: {RENDER_URL}")
    print(f"Repeticiones por ruta: 3")
    print(f"Inicio: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*85}\n")
    
    resultados = []
    
    for nombre, ruta in RUTAS.items():
        print(f"Midiendo {nombre:<25}", end=" ", flush=True)
        resultado = medir_velocidad_ruta(ruta, nombre)
        resultados.append(resultado)
        
        if resultado["promedio"]:
            print(f"✓ {resultado['promedio']*1000:>6.0f}ms")
        else:
            print(f"✗ Error ({resultado['errores']} fallos)")
    
    # Reporte
    print(f"\n{'='*85}")
    print(f"RESULTADOS DE VELOCIDAD")
    print(f"{'='*85}\n")
    
    print(f"{'Ruta':<30} | {'Promedio':<12} | {'Mín':<10} | {'Máx':<10} | {'Estado':<8}")
    print("-" * 85)
    
    for r in resultados:
        if r["promedio"]:
            if r["promedio"] < 1:
                estado = "✓ RÁPIDO"
            elif r["promedio"] < 2:
                estado = "⚠ OK"
            else:
                estado = "✗ LENTO"
            print(f"{r['nombre']:<30} | {r['promedio']*1000:>10.0f}ms | "
                  f"{r['min']*1000:>8.0f}ms | {r['max']*1000:>8.0f}ms | {estado:<8}")
        else:
            print(f"{r['nombre']:<30} | {'ERROR':<12} | {' '*10} | {' '*10} | ✗ FALLO")
    
    # Análisis
    print(f"\n{'='*85}")
    print(f"ANÁLISIS")
    print(f"{'='*85}\n")
    
    velocidades = [r["promedio"] for r in resultados if r["promedio"]]
    
    if velocidades:
        print(f"Tiempo promedio de todas las rutas: {statistics.mean(velocidades)*1000:.0f}ms")
        
        try:
            mas_rapida = min([r for r in resultados if r["promedio"]], key=lambda x: x['promedio'])
            mas_lenta = max([r for r in resultados if r["promedio"]], key=lambda x: x['promedio'])
            
            print(f"Ruta más rápida: {mas_rapida['nombre']} ({mas_rapida['promedio']*1000:.0f}ms)")
            print(f"Ruta más lenta: {mas_lenta['nombre']} ({mas_lenta['promedio']*1000:.0f}ms)")
        except (ValueError, IndexError):
            print("No hay datos de velocidad para analizar")
        
        rutas_lentas = [r for r in resultados if r["promedio"] and r["promedio"] > 2]
        if rutas_lentas:
            print(f"\nRutas que tardan >2s (considera optimización):")
            for r in rutas_lentas:
                print(f"  - {r['nombre']}: {r['promedio']*1000:.0f}ms")
        else:
            print(f"\n✓ Todas las rutas responden en menos de 2 segundos")
    else:
        print("⚠ ERROR: No se pudieron medir las rutas")
        print(f"Verifica que:")
        print(f"  1. RENDER_URL está correctamente configurada: {RENDER_URL}")
        print(f"  2. La app en Render está disponible")
        print(f"  3. Tienes conexión a Internet")
        print(f"\nPara cambiar la URL, edita este archivo y reemplaza:")
        print(f"  RENDER_URL = '{RENDER_URL}'")

if __name__ == "__main__":
    test_velocidad()
