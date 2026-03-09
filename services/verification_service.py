"""
Servicio de verificación de correos electrónicos
"""
import secrets
import string
from datetime import datetime, timedelta
from models.database import db
from models.models import VerificationCodeModel


class VerificationCode:
    """Modelo para almacenar códigos de verificación"""
    
    @staticmethod
    def generate_code(length=6):
        """Genera un código de 6 dígitos numéricos"""
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    @staticmethod
    def crear_codigo(email, tipo='email_verification'):
        """
        Crea un código de verificación para un email.
        
        Args:
            email: email del usuario
            tipo: tipo de verificación ('email_verification', 'password_reset', etc)
        
        Returns:
            código generado
        """
        try:
            # Limpiar códigos expirados/usados
            VerificationCodeModel.limpiar_expirados()
            
            # Generar código
            codigo = VerificationCode.generate_code()
            
            # Eliminar códigos previos del mismo tipo para este email
            VerificationCodeModel.query.filter_by(email=email, tipo=tipo).delete()
            
            # Crear nuevo código
            vc = VerificationCodeModel(
                email=email,
                code=codigo,
                tipo=tipo,
                expires_at=datetime.utcnow() + timedelta(minutes=15)
            )
            db.session.add(vc)
            db.session.commit()
            
            print(f"[VERIFICATION] Código {tipo} generado para {email}: {codigo}")
            return codigo
        except Exception as e:
            print(f"[ERROR] Creando código de verificación: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def validar_codigo(email, codigo, tipo='email_verification'):
        """
        Valida un código de verificación.
        
        Args:
            email: email del usuario
            codigo: código a validar
            tipo: tipo de verificación esperado
        
        Returns:
            True si el código es válido, False en caso contrario
        """
        try:
            vc = VerificationCodeModel.query.filter_by(
                email=email,
                code=codigo,
                tipo=tipo,
                used=False
            ).first()
            
            if not vc:
                print(f"[VERIFICATION] Código no encontrado para {email}")
                return False
            
            if vc.is_expired():
                print(f"[VERIFICATION] Código expirado para {email}")
                vc.mark_as_used()
                return False
            
            # Marcar como usado
            vc.mark_as_used()
            print(f"[VERIFICATION] Código validado correctamente para {email}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Validando código: {e}")
            return False


class VerificationEmail:
    """Generador de templates HTML para emails de verificación"""
    
    @staticmethod
    def template_verificacion(nombre, codigo):
        """Template HTML para email de verificación de cuenta"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 40px auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; }}
                .content p {{ color: #555; line-height: 1.6; margin: 15px 0; }}
                .code-box {{ background: #f0f0f0; border-left: 4px solid #2c3e50; padding: 15px 20px; margin: 25px 0; border-radius: 4px; }}
                .code {{ font-size: 32px; font-weight: bold; color: #2c3e50; letter-spacing: 5px; text-align: center; }}
                .footer {{ background: #f9f9f9; padding: 20px; text-align: center; color: #999; font-size: 12px; border-top: 1px solid #eee; }}
                .footer p {{ margin: 5px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧺 La Lavandería</h1>
                </div>
                <div class="content">
                    <p>¡Hola {nombre}!</p>
                    <p>Gracias por registrarte en <strong>La Lavandería</strong>. Para completar tu registro, usa el siguiente código de verificación:</p>
                    <div class="code-box">
                        <div class="code">{codigo}</div>
                    </div>
                    <p>Este código expira en <strong>15 minutos</strong>.</p>
                    <p>Si no solicitaste esta verificación, puedes ignorar este email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 La Lavandería. Todos los derechos reservados.</p>
                    <p>Este es un correo automático, por favor no respondas.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def template_reseteo_contrasena(nombre, codigo):
        """Template HTML para email de reseteo de contraseña"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 40px auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #c0392b 0%, #e74c3c 100%); color: white; padding: 30px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; }}
                .content p {{ color: #555; line-height: 1.6; margin: 15px 0; }}
                .code-box {{ background: #f0f0f0; border-left: 4px solid #c0392b; padding: 15px 20px; margin: 25px 0; border-radius: 4px; }}
                .code {{ font-size: 32px; font-weight: bold; color: #c0392b; letter-spacing: 5px; text-align: center; }}
                .footer {{ background: #f9f9f9; padding: 20px; text-align: center; color: #999; font-size: 12px; border-top: 1px solid #eee; }}
                .footer p {{ margin: 5px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Resetear Contraseña</h1>
                </div>
                <div class="content">
                    <p>¡Hola {nombre}!</p>
                    <p>Recibimos una solicitud para resetear tu contraseña. Usa el siguiente código para continuar:</p>
                    <div class="code-box">
                        <div class="code">{codigo}</div>
                    </div>
                    <p>Este código expira en <strong>15 minutos</strong>.</p>
                    <p>Si no solicitaste un reseteo de contraseña, ignora este email y tu contraseña permanecerá igual.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 La Lavandería. Todos los derechos reservados.</p>
                    <p>Este es un correo automático, por favor no respondas.</p>
                </div>
            </div>
        </body>
        </html>
        """


def enviar_email_verificacion(email, nombre):
    """
    Envía un email de verificación con código al usuario.
    
    Args:
        email: email del usuario
        nombre: nombre del usuario
    
    Returns:
        código generado
    """
    from services.email_service import send_email_async
    
    # Generar código
    codigo = VerificationCode.crear_codigo(email, 'email_verification')
    if not codigo:
        return None
    
    # Generar HTML
    html = VerificationEmail.template_verificacion(nombre, codigo)
    
    # Enviar email
    send_email_async(
        destinatario=email,
        asunto='Verifica tu cuenta en La Lavandería',
        cuerpo_html=html
    )
    
    return codigo


def enviar_email_reseteo_contrasena(email, nombre):
    """
    Envía un email para reseteo de contraseña con código.
    
    Args:
        email: email del usuario
        nombre: nombre del usuario
    
    Returns:
        código generado
    """
    from services.email_service import send_email_async
    
    # Generar código
    codigo = VerificationCode.crear_codigo(email, 'password_reset')
    if not codigo:
        return None
    
    # Generar HTML
    html = VerificationEmail.template_reseteo_contrasena(nombre, codigo)
    
    # Enviar email
    send_email_async(
        destinatario=email,
        asunto='Resetea tu contraseña en La Lavandería',
        cuerpo_html=html
    )
    
    return codigo
