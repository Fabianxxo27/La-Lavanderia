@echo off
REM Ejecutador de pruebas de carga en Render
REM Uso: tests\run_tests.bat

setlocal enabledelayedexpansion

cls
echo.
echo ============================================================
echo PRUEBAS DE CARGA EN RENDER - La Lavanderia
echo ============================================================
echo.

REM Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado
    pause
    exit /b 1
)

REM Verifica dependencias
echo Verificando dependencias...
pip list | find "locust" >nul
if errorlevel 1 (
    echo Instalando locust y requests...
    pip install locust requests
)

echo.
echo Selecciona una prueba:
echo.
echo 1) Test de Velocidad (RECOMENDADO PARA EMPEZAR)
echo 2) Test de Carga con Locust (Visual, Mejor para Demostrar)
echo 3) Test de Resistencia (Carga Prolongada)
echo 4) Ejecutar TODAS las pruebas en secuencia
echo.

set /p opcion="Opcion (1-4): "

if "%opcion%"=="1" (
    echo.
    echo Iniciando Test de Velocidad...
    echo.
    python tests\test_velocidad_render.py
) else if "%opcion%"=="2" (
    echo.
    echo Iniciando Locust...
    echo.
    echo Se abrira dashboard en http://localhost:8089
    echo.
    locust -f tests\locustfile_render.py --users 20 --spawn-rate 2
) else if "%opcion%"=="3" (
    echo.
    echo Iniciando Test de Resistencia (10 minutos)...
    echo.
    python tests\test_resistencia_render.py
) else if "%opcion%"=="4" (
    echo.
    echo Ejecutando TODAS las pruebas...
    echo.
    
    echo === PASO 1: Test de Velocidad ===
    python tests\test_velocidad_render.py
    
    echo.
    echo === PASO 2: Test de Resistencia ===
    timeout /t 5
    python tests\test_resistencia_render.py
    
    echo.
    echo === PASO 3: Test de Carga (Locust) ===
    timeout /t 5
    locust -f tests\locustfile_render.py --headless --users 20 --run-time 5m
) else (
    echo Opcion invalida
)

echo.
pause
