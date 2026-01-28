# 1. Imagen Base: Cambiado a Python 3.9 y 'bullseye' para solucionar el error 404
FROM python:3.9-slim-bullseye

WORKDIR /app

# 2. INSTALACIÓN DE DEPENDENCIAS DEL SISTEMA (CLAVE para Pandas/NumPy)
# Esto instala las herramientas de compilación y las librerías matemáticas necesarias.
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libatlas-base-dev \
    gfortran \
    gunicorn \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. Instalación de Dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copia el Código de la Aplicación
COPY . .

# 5. Comando de Inicio (CMD) para Flask con Gunicorn o Waitress
ENV PORT 8080
# Puedes usar gunicorn o waitress, ambos funcionan bien con Render
CMD ["sh", "-c", "python app.py"]

