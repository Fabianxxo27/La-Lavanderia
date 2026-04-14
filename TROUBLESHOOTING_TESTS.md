# 🔧 Troubleshooting - Pruebas de Carga

## Errores Comunes y Soluciones

---

## ❌ Error: "ModuleNotFoundError: No module named 'requests'"

### Causa
`requests` no está instalado.

### Solución
```bash
pip install requests
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
Las pruebas están esperando respuesta del servidor.

### Solución

Aumenta el timeout o reduce el número de usuarios:

**test_carga_requests.py:**
```python
USUARIOS_SIMULTANEOS = 5  # Reduce de 10 a 5
DURACION_SEGUNDOS = 60     # Reduce de 120 a 60
```

---

## ❌ Error: "Connection refused" o "Connection timed out"

### Causa
Tu aplicación en Render no está disponible.

### Solución

1. **Verifica que Render está activo**
   - Abre tu URL en navegador
   - ¿Te carga la página?

2. **Verifica la URL** (IMPORTANTE)
   En los scripts, busca:
   ```python
   RENDER_URL = os.getenv("RENDER_URL", "https://la-lavanderia.onrender.com")
   ```
   Reemplaza con tu URL real.

3. **Verifica conexión a Internet**
   ```bash
   ping google.com
   ```

4. **Render puede estar hibernando**
   Si tu app está en plan FREE:
   - Abre la URL en navegador
   - Espera a que cargue (~30 segundos)
   - Intenta nuevamente

---

## ❌ Error: "SSLError" en Locust

### Causa
`geventhttpclient` (que Locust usa internamente) tiene problemas con SSL en Windows.

### Solución

**Opción A: Usa el script que NO usa Locust (RECOMENDADO)**
```bash
python tests/test_carga_requests.py
```

**Opción B: Deshabilita SSL manualmente**
```bash
set PYTHONHTTPSVERIFY=0
locust -f tests/locustfile_render.py --users 10 --run-time 2m
```

**Opción C: Mac/Linux**
```bash
export PYTHONHTTPSVERIFY=0
locust -f tests/locustfile_render.py --users 10 --run-time 2m
```

---

## ❌ Error: "name 'requests' is not defined"

### Causa
requests se importó pero no está disponible.

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
- Dice que está corriendo
- Pero http://localhost:8089 no carga

### Solución

1. **Espera 10-15 segundos** (Locust tarda en iniciarse)

2. **Abre manualmente en navegador:**
   http://localhost:8089

3. **Verifica que el puerto está libre**
   ```bash
   netstat -ano | findstr :8089
   ```
   Si muestra algo, intenta otro puerto:
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
3. Hay error de autenticación

### Solución

1. **Verifica la URL en los scripts**
   ```bash
   grep "RENDER_URL" tests/*.py
   ```

2. **Prueba la URL manualmente en navegador**
   ¿Funciona?

3. **Revisa las credenciales**
   Los scripts usan:
   - Username: `testuser1`
   - Password: `TestPassword123!`
   
   ¿Existen estos usuarios en tu BD?

---

## ❌ Error: "pip: command not found"

### Causa
Python o pip no están en el PATH.

### Solución

**Opción A: Usa python -m pip**
```bash
python -m pip install requests locust
```

**Opción B: Reinstala Python**
- https://www.python.org/downloads/
- Durante instalación, marca: ☑ Add Python to PATH

---

## ❌ Error: "ConnectionError"

### Causa
La conexión se perdió a mitad de la prueba.

### Solución

**Opción 1: Aumenta timeout**
En `test_carga_requests.py`:
```python
timeout=30  # Cambia a 60
```

**Opción 2: Reduce usuarios**
```python
USUARIOS_SIMULTANEOS = 5  # En lugar de 10
```

**Opción 3: Verifica recursos de Render**
- Ve a tu dashboard de Render
- Revisa CPU y memoria

---

## ✅ ¿Nada de esto funciona?

### Debug Avanzado

1. **Verifica que RENDER_URL está bien**
   ```bash
   python -c "import os; print(os.getenv('RENDER_URL', 'da'))"
   ```

2. **Intenta conectar manualmente**
   ```python
   python
   >>> import requests
   >>> r = requests.get("https://tu-url.onrender.com/", verify=False)
   >>> print(r.status_code)
   ```
   Si dice `200`, la URL funciona.

3. **Revisa logs de Render**
   - Ve a https://dashboard.render.com
   - Selecciona tu servicio
   - Mira los "Logs"

4. **Prueba en otra máquina**

---

## 📞 Última Opción

Copia y pega esto para diagnosticar:

```bash
python -c "
import sys
print('Python:', sys.version)
import requests
print('Requests:', requests.__version__)
try:
    from locust import __version__ as locust_version
    print('Locust:', locust_version)
except:
    print('Locust: NOT INSTALLED')
r = requests.get('https://tu-url.onrender.com/', verify=False, timeout=10)
print('Status:', r.status_code)
"
```

Comparte el output en caso de duda.
