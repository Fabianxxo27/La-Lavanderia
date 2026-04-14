# Pruebas de Estrés en Render

Scripts para ejecutar pruebas de carga en tu aplicación en la nube (Render).

---

## Instalación

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

### 2. Test de Carga (Visual, Mejor para Demostración)

Simula múltiples usuarios simultáneos.

```bash
# Interfaz web (recomendado para ver en tiempo real)
locust -f tests/locustfile_render.py --users 20 --spawn-rate 2 --run-time 5m
# Abre http://localhost:8089

# Sin interfaz (más rápido)
locust -f tests/locustfile_render.py --headless --users 20 --spawn-rate 2 --run-time 5m
```

**Parámetros:**
- `--users 20` - Número de usuarios simultáneos
- `--spawn-rate 2` - Cuántos usuarios por segundo crear
- `--run-time 5m` - Duración de la prueba

**Pruebas recomendadas:**
```bash
# Prueba suave
locust -f tests/locustfile_render.py --users 5 --spawn-rate 1 --run-time 2m

# Prueba normal
locust -f tests/locustfile_render.py --users 20 --spawn-rate 2 --run-time 5m

# Prueba de estrés
locust -f tests/locustfile_render.py --users 50 --spawn-rate 5 --run-time 10m
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
