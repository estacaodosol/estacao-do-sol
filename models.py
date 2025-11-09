from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ================================
# Usuário
# ================================
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    perfil = db.Column(db.String(20), nullable=True, default='morador')

    # Relacionamentos
    pedidos = db.relationship('Pedido', backref='usuario', lazy=True)
    morador = db.relationship('Morador', backref='usuario', uselist=False)

# ================================
# Morador
# ================================
class Morador(db.Model):
    __tablename__ = 'moradores'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    apartamento_id = db.Column(db.Integer, db.ForeignKey('apartamentos.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20))
    ativo = db.Column(db.Boolean, default=True)

# ================================
# Apartamento
# ================================
class Apartamento(db.Model):
    __tablename__ = 'apartamentos'
    id = db.Column(db.Integer, primary_key=True)
    bloco = db.Column(db.String(10))
    numero = db.Column(db.String(10), nullable=False)

    moradores = db.relationship('Morador', backref='apartamento_obj', lazy=True)

# ================================
# Serviço
# ================================
class Servico(db.Model):
    __tablename__ = 'servicos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)

class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    servico_id = db.Column(db.Integer, db.ForeignKey('servicos.id'), nullable=False)
    nome = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Pendente')
    observacao = db.Column(db.Text, nullable=True)
    data = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # relacionamento correto
    servico = db.relationship('Servico', backref='pedidos')
