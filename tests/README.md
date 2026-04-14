# Pruebas de Estrés en Render

Scripts para ejecutar pruebas de carga en tu aplicación en la nube (Render).

---

## Inicio Rápido

### Opción A: Ejecutar con Script (Más Fácil)

**Windows:**
```bash
tests\run_tests.bat
```

Selecciona la opción que deseas (recomendado: opción 2 para sin errores de SSL).

**Mac/Linux:**
```bash
bash tests/run_tests.sh
```

---

### Opción B: Instalar Dependencias Manualmente

```bash
pip install locust requests
```

---

## Configurar URL de Render

Antes de ejecutar, reemplaza la URL en cada script:

**Opción 1: Editar archivos (rápido)**
- Abre cada `.py`
- Busca: `RENDER_URL = os.getenv("RENDER_URL", "https://la-lavanderia.onrender.com")`
- Reemplaza `https://la-lavanderia.onrender.com` con tu URL real

**Opción 2: Variable de entorno (mejor)**
```bash
# Windows PowerShell
$env:RENDER_URL = "https://tu-url-render.onrender.com"

# Mac/Linux
export RENDER_URL="https://tu-url-render.onrender.com"
```

---

## Pruebas Disponibles

> **Nota:** Los scripts están configurados para ignorar/deshabilitar errores de certificados SSL (común en pruebas de carga). Si ves advertencias de SSL, es normal y se pueden ignorar.

### 1. Test de Velocidad (COMIENZA AQUÍ)

Mide cuánto tarda cada página en responder.

```bash
python tests/test_velocidad_render.py
```

**Duración:** ~2 minutos  
**Output:** Tabla de tiempos de respuesta  

```
Ruta                    | Promedio    | Mín       | Máx       | Estado
Homepage                |  1250ms     |  950ms    | 1650ms    | ⚠ OK
Cliente Inicio          |   850ms     |  750ms    | 1050ms    | ✓ RÁPIDO
Admin Inicio            |  1850ms     |  1700ms   | 2200ms    | ✗ LENTO
```

---

### 2b. Test de Carga (Requests, Sin Errores SSL - RECOMENDADO)

Prueba de carga usando `requests` directamente, sin Locust.

> **Ventaja:** Evita completamente los errores de SSL de Windows

```bash
python tests/test_carga_requests.py
```

**Duración:** ~2 minutos  
**Output:** Estadísticas de carga

```
=======================================================================
RESULTADOS FINALES
=======================================================================
Tiempo total: 120.5s
Requests exitosos: 1245
Requests fallidos: 15
Tasa de éxito: 98.8%
Requests por segundo: 10.35

Tiempos de respuesta:
  Promedio: 850ms
  Mínimo: 150ms
  Máximo: 2500ms
  Mediana: 750ms

✓ Prueba exitosa: App aguanta bien la carga
=======================================================================
```

O desde el script automatizado:
```bash
tests\run_tests.bat
# Selecciona opción 2
```

---

### 2. Test de Carga (Locust, Visual, Mejor para Demostración)

Simula múltiples usuarios simultáneos.

**Opción A: Script automatizado (Recomendado - Evita errores de SSL)**
```bash
tests\run_locust.bat
# O con parámetros personalizados:
tests\run_locust.bat --users 10 --run-time 5m
```

**Opción B: Comando manual - Interfaz web**
```bash
locust -f tests/locustfile_render.py --users 20 --spawn-rate 2 --run-time 5m
# Abre: http://localhost:8089
```

**Opción C: Comando manual - Sin interfaz**
```bash
locust -f tests/locustfile_render.py --headless --users 20 --spawn-rate 2 --run-time 5m
```

**Parámetros comunes:**
- `--users 20` - Número de usuarios simultáneos
- `--spawn-rate 2` - Cuántos usuarios por segundo crear
- `--run-time 5m` - Duración de la prueba

**Si tienes errores de SSL** (solo en Windows):

Usa la versión alternativa:
```bash
locust -f tests/locustfile_requests_render.py --users 10 --spawn-rate 1 --run-time 5m
# Abre: http://localhost:8089
```

**Pruebas recomendadas:**
```bash
# Prueba suave
tests\run_locust.bat --users 5 --run-time 2m

# Prueba normal
tests\run_locust.bat --users 20 --run-time 5m

# Prueba de estrés
tests\run_locust.bat --users 50 --run-time 10m
```

---

### 3. Test de Resistencia

Mantiene carga durante tiempo prolongado (detecta memory leaks).

```bash
python tests/test_resistencia_render.py
```

**Duración:** ~10 minutos (editable en el script)  
**Output:** Reporte cada minuto  

```
[+01min] OPs:   425 | Éxito:   425 | Fallos:     0 | Tasa:  100.0%
[+02min] OPs:   850 | Éxito:   850 | Fallos:     0 | Tasa:  100.0%
[+03min] OPs:  1275 | Éxito:  1230 | Fallos:    45 | Tasa:   96.5%
```

---

## Ejemplos de Uso

### Ejemplo 1: Prueba Rápida (Total 3 minutos)

```bash
python tests/test_velocidad_render.py
```

### Ejemplo 2: Prueba Completa (Total 15 minutos)

```bash
# Terminal 1: Velocidad (2 min)
python tests/test_velocidad_render.py

# Terminal 2: Carga (5 min)
locust -f tests/locustfile_render.py --headless --users 20 --run-time 5m

# Terminal 3: Resistencia (8 min)
python tests/test_resistencia_render.py
```

### Ejemplo 3: Demostración en Vivo (Para defensa)

```bash
locust -f tests/locustfile_render.py --users 20 --spawn-rate 2 --run-time 10m
# Abre navegador en http://localhost:8089
# Muestra el dashboard actualizándose en vivo
```

---

## Interpretación de Resultados

### Tiempos de Respuesta

| Tiempo | Interpretación |
|--------|----------------|
| <500ms | Excelente |
| 500-1000ms | Bueno |
| 1000-2000ms | Aceptable |
| >2000ms | Lento, revisar |

### Tasa de Error

| Tasa | Interpretación |
|------|----------------|
| 0% | Perfecto |
| <1% | Muy bueno |
| 1-5% | Aceptable |
| >5% | Revisar problemas |

### Qué significa en Locust

- **Name:** Ruta probada
- **Count:** Número de requests
- **Failure:** Numero de errores
- **Avg:** Tiempo promedio de respuesta
- **Min/Max:** Tiempo mínimo y máximo
- **req/s:** Requests por segundo que aguanta

---

## Troubleshooting

### Error: "Connection refused"
La aplicación en Render no está disponible. Verifica:
- URL es correcta
- Render está activo (no hibernando)
- Render tiene conexión a BD

### Error: "Timeout"
Render está respondiendo lentamente.
- Puede ser plan free (ciclo sueño)
- Prueba con menos usuarios

### Locust no muestra datos
Espera 10-15 segundos, tarda en conectar.

---

## Para la Defensa

**Lo que mostrar:**

1. Ejecuta `test_velocidad_render.py`
2. Muestra la tabla de resultados
3. Abre Locust con 20 usuarios
4. Muestra dashboard actualizándose
5. Comenta: "Mi app soporta X usuarios con tiempo de respuesta de Y ms"

**Evidencias a capturar:**
- Terminal mostrando test_velocidad_render.py
- Dashboard de Locust con gráficos
- Tabla de resultados
- URL de Render funcionando

---

## Más Información

Ver: `PRUEBAS_DE_ESTRES_EN_RENDER.md` para más detalles y explicaciones.
