# 1. Imagen Base
FROM python:3.10-slim-buster

WORKDIR /app

# 2. INSTALACIÓN DE DEPENDENCIAS DEL SISTEMA (CLAVE para solucionar la compilación de Pandas/NumPy)
# Esto proporciona las herramientas C/C++ (build-essential, gfortran) y la librería matemática (libatlas-base-dev)
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libatlas-base-dev \
    gfortran \
    # Instalar Gunicorn, ya que es el servidor de producción necesario
    gunicorn \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. Instalación de Dependencias de Python
# Esto ejecutará pip install -r requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copia el Código de la Aplicación
COPY . .

# 5. Comando de Inicio (CMD) para Flask con Gunicorn
# Railway usará este comando para iniciar tu servidor web.
ENV PORT 8080
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]
