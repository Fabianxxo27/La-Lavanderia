# 🔧 Troubleshooting - Pruebas de Carga

## Errores Comunes y Soluciones

---

## ❌ Error: "ModuleNotFoundError: No module named 'requests'"

### Causa
`requests` no está instalado en tu entorno de Python.

### Solución
```bash
pip install requests
```

O instala ambas dependencias:
```bash
pip install locust requests
```

---

## ❌ Error: "ModuleNotFoundError: No module named 'locust'"

### Causa
`locust` no está instalado.

### Solución
```bash
pip install locust
```

---

## ❌ El script "se congela" o demora mucho

### Causa
Las pruebas están esperando respuesta del servidor en Render.

### Solución

**Opción 1: Reducir el timeout**
Abre el script (`test_velocidad_render.py`) y cambia:
```python
response = requests.get(
    f"{RENDER_URL}{ruta}",
    timeout=30,  # Cambia a 10
    allow_redirects=True
)
```

**Opción 2: Reducir repeticiones**
En el mismo archivo:
```python
repeticiones=3  # Cambia a 1
```

---

## ❌ Error: "Connection refused" o "Connection timed out"

### Causa
Tu aplicación en Render no está disponible.

### Solución

1. **Verifica que Render está activo**
   - Abre tu navegador
   - Ve a tu URL de Render
   - ¿Te carga la página?

2. **Verifica la URL**
   En los scripts, busca:
   ```python
   RENDER_URL = "https://la-lavanderia.onrender.com"
   ```
   ¿Qué URL está ahí? Debe ser la misma que ves en el navegador.

3. **Verifica la conexión a Internet**
   ```bash
   ping google.com
   ```

4. **Espera a que Render despierte**
   Si tu app está en el plan FREE de Render, puede estar "dormida" (después de 15 min sin usar).
   - Abre la URL en el navegador
   - Espera a que cargue (~30 segundos)
   - Intenta el test nuevamente

---

## ❌ Error: "URL incorrecta"

### Solución

La URL por defecto en los scripts es: `https://la-lavanderia.onrender.com`

Necesitas cambiarla a tu URL real de Render (ej: `https://mi-app-bonita.onrender.com`)

**Opción A: Editar cada archivo**
1. Abre `tests/test_velocidad_render.py`
2. En la línea 17, modifica:
   ```python
   RENDER_URL = "https://tu-url-real.onrender.com"
   ```
3. Haz lo mismo en `test_resistencia_render.py` y `locustfile_render.py`

**Opción B: Usar variable de entorno**
```bash
# Windows PowerShell
$env:RENDER_URL = "https://tu-url-real.onrender.com"
python tests/test_velocidad_render.py

# Mac/Linux
export RENDER_URL="https://tu-url-real.onrender.com"
python tests/test_velocidad_render.py
```

---

## ❌ Error: "name 'requests' is not defined"

### Causa
`requests` se importó pero no está disponible.

### Solución
```bash
pip install --upgrade requests
```

Si sigue fallando:
```bash
pip uninstall requests -y
pip install requests
```

---

## ❌ Locust no abre el dashboard

### Síntomas
- Ejecutas: `locust -f tests/locustfile_render.py`
- Terminal dice que está corriendo
- Pero http://localhost:8089 no carga

### Solución

1. **Espera más tiempo**
   Locust tarda ~10-15 segundos en iniciarse

2. **Abre http://localhost:8089 manualmente**
   En tu navegador, escribe esa dirección

3. **Verifica que el puerto está libre**
   ```bash
   netstat -ano | findstr :8089
   ```
   Si muestra algo, hay algo ocupando ese puerto. Intenta:
   ```bash
   locust -f tests/locustfile_render.py --web-port 8090
   # Abre http://localhost:8090
   ```

4. **Intenta sin interfaz gráfica**
   ```bash
   locust -f tests/locustfile_render.py --headless --users 10 --run-time 2m
   ```

---

## ❌ Error: "El test muestra 0% de éxito"

### Causa
Todas las requests están fallando.

### Probable razón
1. La URL es incorrecta
2. Render está caído
3. Hay error de autenticación (las rutas requieren login)

### Solución

1. **Verifica la URL en los scripts**
   ```bash
   grep "RENDER_URL" tests/*.py
   ```

2. **Abre manualmente la URL en navegador**
   ¿Funciona?

3. **Revisa las credenciales de login**
   Los scripts usan:
   - Username: `testuser1`
   - Password: `TestPassword123!`
   
   ¿Existen estos usuarios en tu BD?

---

## ❌ Error: "pip: command not found"

### Causa
Python o pip no están en el PATH del sistema.

### Solución

**Opción A: Usa python -m pip**
```bash
python -m pip install locust requests
```

**Opción B: Verifica Python**
```bash
python --version
```

Si no funciona, reinstala Python:
- https://www.python.org/downloads/
- Durante instalación, marca: ☑ Add Python to PATH

---

## ❌ Error: "ConnectionError: ('Connection aborted.'"

### Causa
La conexión se perdió a mitad de la prueba.

### Solución

**Opción 1: Aumentar timeout**
```python
timeout=30  # Cambia a 60
```

**Opción 2: Reducir usuarios simultáneos**
En locust:
```bash
locust -f tests/locustfile_render.py --users 5 --run-time 2m
```

**Opción 3: Verificar que Render tiene suficientes recursos**
- Ve a tu dashboard de Render
- Revisa CPU y memoria

---

## ✅ ¿Nada de esto funciona?

### Debug avanzado

1. **Verifica que RENDER_URL está bien**
   ```bash
   python -c "import os; print(os.getenv('RENDER_URL', 'https://la-lavanderia.onrender.com'))"
   ```

2. **Intenta conectar manualmente**
   ```python
   python
   >>> import requests
   >>> r = requests.get("https://tu-url.onrender.com/")
   >>> print(r.status_code)
   ```
   Si dice `200`, la URL funciona

3. **Revisa logs de Render**
   - Ve a https://dashboard.render.com
   - Selecciona tu servicio
   - Mira los "Logs"

4. **Prueba en otra máquina**
   Para ver si es problema local

---

## 📞 Última Opción

Si nada funciona, copia y pega esto para diagnosticar:

```bash
python -c "
import sys
print('Python:', sys.version)
import requests
print('Requests:', requests.__version__)
from locust import __version__ as locust_version
print('Locust:', locust_version)
r = requests.get('https://tu-url.onrender.com/')
print('Status:', r.status_code)
"
```

Comparte el output.
