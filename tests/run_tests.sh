#!/bin/bash
# Ejecutador de pruebas de carga en Render
# Uso: bash tests/run_tests.sh

clear

echo "============================================================"
echo "PRUEBAS DE CARGA EN RENDER - La Lavanderia"
echo "============================================================"
echo ""

# Verifica Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python no esta instalado"
    exit 1
fi

# Verifica dependencias
echo "Verificando dependencias..."
if ! pip list | grep -i locust > /dev/null; then
    echo "Instalando locust y requests..."
    pip install locust requests
fi

echo ""
echo "Selecciona una prueba:"
echo ""
echo "1) Test de Velocidad (RECOMENDADO PARA EMPEZAR)"
echo "2) Test de Carga con Locust (Visual, Mejor para Demostrar)"
echo "3) Test de Resistencia (Carga Prolongada)"
echo "4) Ejecutar TODAS las pruebas en secuencia"
echo ""

read -p "Opcion (1-4): " opcion

case $opcion in
    1)
        echo ""
        echo "Iniciando Test de Velocidad..."
        echo ""
        python3 tests/test_velocidad_render.py
        ;;
    2)
        echo ""
        echo "Iniciando Locust..."
        echo ""
        echo "Se abrira dashboard en http://localhost:8089"
        echo ""
        locust -f tests/locustfile_render.py --users 20 --spawn-rate 2
        ;;
    3)
        echo ""
        echo "Iniciando Test de Resistencia (10 minutos)..."
        echo ""
        python3 tests/test_resistencia_render.py
        ;;
    4)
        echo ""
        echo "Ejecutando TODAS las pruebas..."
        echo ""
        
        echo "=== PASO 1: Test de Velocidad ==="
        python3 tests/test_velocidad_render.py
        
        echo ""
        echo "=== PASO 2: Test de Resistencia ==="
        sleep 5
        python3 tests/test_resistencia_render.py
        
        echo ""
        echo "=== PASO 3: Test de Carga (Locust) ==="
        sleep 5
        locust -f tests/locustfile_render.py --headless --users 20 --run-time 5m
        ;;
    *)
        echo "Opcion invalida"
        exit 1
        ;;
esac

echo ""
