"""
Configuración de la aplicación Flask
"""
import os
import secrets
import datetime
import urllib.parse
from dotenv import load_dotenv
import credentials as cd

# Cargar variables de entorno desde .env (si existe)
load_dotenv()


class Config:
    """Configuración base de la aplicación"""
    
    # Secret key segura
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    if len(SECRET_KEY) < 16:
        SECRET_KEY = secrets.token_hex(32)
        print("[WARN] Usando SECRET_KEY generada automáticamente")
    
    # Configuración de sesión segura
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(hours=2)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB máximo
    
    # Configuración de la base de datos
    # En Render: usar DATABASE_URL desde variables de entorno (PostgreSQL)
    # En desarrollo local: usar credentials.py (MySQL/PostgreSQL)
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        # Si no hay DATABASE_URL, usar credenciales locales
        print("⚠️ DATABASE_URL no encontrado, usando credentials.py (desarrollo local)")
        pwd = urllib.parse.quote_plus(cd.password)
        DATABASE_URL = f"postgresql://{cd.user}:{pwd}@{cd.host}/{cd.db}"
    else:
        # Si viene de Render, convertir postgres:// a postgresql://
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        print("✓ Usando DATABASE_URL desde Render (PostgreSQL)")
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    print(f"✓ Base de datos configurada: {DATABASE_URL[:50]}...")
    
    # Configuración de conexión para Render
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 10,
    }
    
    # Desactivar track modifications de SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración SMTP
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER', 'lalavanderiabogota@gmail.com')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
