"""
Servicio de envío de correos electrónicos
"""
import os
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config


def send_email_async(destinatario, asunto, cuerpo_html):
    """
    Envía un correo de forma asíncrona para no bloquear la aplicación.
    
    Args:
        destinatario: email del destinatario
        asunto: asunto del correo
        cuerpo_html: contenido HTML del correo
    """
    def _send():
        try:
            print(f"[MAIL] send_email_async to={destinatario} subject={asunto}", flush=True)
            if not destinatario or '@' not in destinatario:
                print(f"[WARN] Email destinatario invalido: {destinatario}", flush=True)
                return

            # Configuración SMTP
            smtp_server = Config.SMTP_SERVER
            smtp_port = Config.SMTP_PORT
            smtp_user = Config.SMTP_USER
            smtp_password = Config.SMTP_PASSWORD
            
            if not smtp_password:
                print("[WARN] SMTP_PASSWORD no configurado en las variables de entorno", flush=True)
                print("[WARN] Dashboard > Environment > Add Variable > SMTP_PASSWORD", flush=True)
                return
            
            # Crear mensaje
            mensaje = MIMEMultipart('alternative')
            mensaje['From'] = f"La Lavanderia <{smtp_user}>"
            mensaje['To'] = destinatario
            mensaje['Subject'] = asunto
            
            # Adjuntar HTML
            parte_html = MIMEText(cuerpo_html, 'html')
            mensaje.attach(parte_html)
            
            # Enviar
            with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
                print("[MAIL] Conectando SMTP...", flush=True)
                server.starttls()
                print("[MAIL] STARTTLS OK", flush=True)
                server.login(smtp_user, smtp_password)
                print("[MAIL] LOGIN OK", flush=True)
                server.send_message(mensaje)
                print("[MAIL] SEND OK", flush=True)
            
            print(f"[OK] Correo enviado a {destinatario}: {asunto}", flush=True)
        except smtplib.SMTPAuthenticationError as e:
            print(f"[ERROR] Autenticacion SMTP: {e}", flush=True)
            print("[ERROR] Verifica SMTP_USER y SMTP_PASSWORD en Render", flush=True)
        except smtplib.SMTPException as e:
            print(f"[ERROR] SMTPException: {e}", flush=True)
        except Exception as e:
            print(f"[ERROR] Enviando correo a {destinatario}: {e}", flush=True)
    
    # Ejecutar en thread separado
    thread = threading.Thread(target=_send)
    thread.daemon = False
    thread.start()
