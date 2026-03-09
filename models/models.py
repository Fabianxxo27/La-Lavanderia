"""
Modelos SQLAlchemy para la aplicación
"""
from datetime import datetime, timedelta
from models.database import db


class VerificationCodeModel(db.Model):
    """Modelo para almacenar códigos de verificación temporal"""
    
    __tablename__ = 'verification_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    code = db.Column(db.String(10), nullable=False, index=True)
    tipo = db.Column(db.String(50), nullable=False)  # 'email_verification', 'password_reset'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=15))
    used = db.Column(db.Boolean, default=False)
    
    __table_args__ = (
        db.UniqueConstraint('email', 'tipo', name='uq_email_tipo'),
    )
    
    def is_expired(self):
        """Verifica si el código ha expirado"""
        return datetime.utcnow() > self.expires_at
    
    def mark_as_used(self):
        """Marca el código como usado"""
        self.used = True
        db.session.commit()
    
    @staticmethod
    def limpiar_expirados():
        """Elimina códigos expirados o usados"""
        VerificationCodeModel.query.filter(
            (VerificationCodeModel.expires_at < datetime.utcnow()) |
            (VerificationCodeModel.used == True)
        ).delete()
        db.session.commit()
