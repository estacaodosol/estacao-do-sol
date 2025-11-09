# app.py

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from datetime import datetime
from zoneinfo import ZoneInfo
from models import db, Usuario, Morador, Apartamento, Servico, Pedido
from functools import wraps
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required


# -------------------------------
# Configuração do app
# -------------------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///condominio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Chave secreta aleatória
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'uma_chave_super_secreta_fixa_123')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# -------------------------------
# Inicialização das extensões
# -------------------------------
db.init_app(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)

# -------------------------------
# Configuração de upload
# -------------------------------
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# -------------------------------
# Fusos horários
# -------------------------------
brasil = ZoneInfo("America/Sao_Paulo")


# -------------------------------
# Funções auxiliares
# -------------------------------
def login_requerido(tipo=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                flash('Você precisa estar logado.', 'warning')
                return redirect(url_for('login'))
            if tipo and session.get('perfil') != tipo:
                flash('Acesso não autorizado.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# -------------------------------
# Decorador para restringir por tipo de usuário
# -------------------------------
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user, login_required



# -------------------------------
# ROTAS DE AUTENTICAÇÃO
# -------------------------------
@app.route('/')
def index():
    return redirect(url_for('login'))

from flask_login import login_user, logout_user, login_required, current_user

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and bcrypt.check_password_hash(usuario.senha, senha):
            # Faz o login de fato
            login_user(usuario)# ✅ IMPORTANTE: mantém a sessão ativa

            flash('Login realizado com sucesso!', 'success')

            if usuario.tipo == 'sindico':
                return redirect(url_for('dashboard_sindico'))
            else:
                return redirect(url_for('dashboard_morador'))
        else:
            flash('E-mail ou senha incorretos.', 'danger')

    return render_template('login.html')

from flask_login import logout_user

@app.route('/logout')
@login_required
def logout():
    logout_user()  # limpa apenas os dados de login do usuário
    flash('Você saiu com sucesso.', 'success')
    return redirect(url_for('login'))

# -------------------------------
# DECORADOR DE TIPO DE USUÁRIO
# -------------------------------
def tipo_requerido(tipo):
    """Decorador para restringir rota a um tipo de usuário específico."""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.tipo != tipo:
                flash("Acesso negado.", "danger")
                if current_user.tipo == 'morador':
                    return redirect(url_for('dashboard_morador'))
                elif current_user.tipo == 'sindico':
                    return redirect(url_for('dashboard_sindico'))
                else:
                    return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        bloco = request.form.get('bloco', '').strip() or None
        numero = request.form['numero'].strip()
        telefone = request.form.get('telefone', '')
        email = request.form['email']
        senha = request.form['senha']

        if Usuario.query.filter_by(email=email).first():
            flash('Email já cadastrado.', 'warning')
            return redirect(url_for('cadastro'))

        # Cria ou encontra apartamento
        apartamento = Apartamento.query.filter_by(bloco=bloco, numero=numero).first()
        if not apartamento:
            apartamento = Apartamento(bloco=bloco, numero=numero)
            db.session.add(apartamento)
            db.session.commit()

        # Cria usuário e morador
        hashed_senha = bcrypt.generate_password_hash(senha).decode('utf-8')
        novo_usuario = Usuario(email=email, senha=hashed_senha, tipo='morador')
        db.session.add(novo_usuario)
        db.session.commit()

        morador = Morador(
            usuario_id=novo_usuario.id,
            apartamento_id=apartamento.id,
            nome=nome,
            telefone=telefone
        )
        db.session.add(morador)
        db.session.commit()

        flash('Cadastro realizado com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))

    return render_template('cadastro.html')

# -------------------------------
# ROTAS DE PERFIL
# -------------------------------
@app.route('/editar_perfil', methods=['GET', 'POST'])
@tipo_requerido('morador')  # apenas moradores podem acessar
def editar_perfil():
    usuario = current_user  # pega o usuário logado pelo Flask-Login
    morador = Morador.query.filter_by(usuario_id=usuario.id).first()
    apartamento = morador.apartamento_obj or Apartamento(bloco='', numero='')

    if request.method == 'POST':
        nome = request.form['nome'].strip()
        bloco = request.form.get('bloco', '').strip() or None
        numero = request.form['numero'].strip()
        telefone = request.form['telefone'].strip()
        email = request.form['email'].strip()
        senha = request.form['senha'].strip()

        # Verifica se o email já existe em outro usuário
        if Usuario.query.filter(Usuario.email==email, Usuario.id!=usuario.id).first():
            flash('Este e-mail já está em uso por outro morador.', 'danger')
            return redirect(url_for('editar_perfil'))

        usuario.email = email
        if senha:
            usuario.senha = bcrypt.generate_password_hash(senha).decode('utf-8')

        morador.nome = nome
        morador.telefone = telefone

        # Atualiza o apartamento, se necessário
        if bloco != (apartamento.bloco or '') or numero != (apartamento.numero or ''):
            apt = Apartamento.query.filter_by(bloco=bloco, numero=numero).first()
            if not apt:
                apt = Apartamento(bloco=bloco, numero=numero)
                db.session.add(apt)
                db.session.commit()
            morador.apartamento_id = apt.id

        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('editar_perfil'))

    return render_template('editar_perfil.html', morador=morador, usuario=usuario, apartamento=apartamento)

# -------------------------------
# ROTAS DE SERVIÇOS
# -------------------------------
@app.route('/cadastrar_servico', methods=['POST'])
@login_requerido('sindico')
def cadastrar_servico():
    nome = request.form.get('nome_servico', '').strip().capitalize()
    if not nome:
        flash('O nome do serviço não pode ser vazio.', 'danger')
        return redirect(url_for('gerenciar_sindico'))

    if Servico.query.filter_by(nome=nome).first():
        flash('Este serviço já está cadastrado.', 'warning')
    else:
        db.session.add(Servico(nome=nome))
        db.session.commit()
        flash(f'Serviço "{nome}" cadastrado com sucesso!', 'success')

    return redirect(url_for('gerenciar_sindico'))

# -------------------------------
# ROTAS DE PEDIDOS
# -------------------------------
@app.route('/novo_pedido', methods=['GET', 'POST'])
@login_required
@tipo_requerido('morador')
def novo_pedido():
    if request.method == 'POST':
        servico_id = request.form.get('servico_id')  # 👈 Nome correto
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')

        if not servico_id:
            flash('Selecione um serviço.', 'warning')
            return redirect(url_for('novo_pedido'))

        novo_pedido = Pedido(
            usuario_id=current_user.id,
            servico_id=servico_id,
            nome=nome,
            descricao=descricao
        )
        db.session.add(novo_pedido)
        db.session.commit()
        flash('Pedido criado com sucesso!', 'success')
        return redirect(url_for('meus_pedidos'))

    servicos_disponiveis = Servico.query.all()
    return render_template('novo_pedido.html', servicos_disponiveis=servicos_disponiveis)


@app.route('/meus_pedidos')
@tipo_requerido('morador')
def meus_pedidos():
    usuario_id = current_user.id
    servico_filtro = request.args.get('servico')
    
    query = Pedido.query.filter_by(usuario_id=usuario_id)
    
    if servico_filtro and servico_filtro.isdigit():
        query = query.filter_by(servico_id=int(servico_filtro))
    
    pedidos = query.order_by(Pedido.data.desc()).all()
    
    # Preparar dados para o template
    pedidos_formatados = []
    for p in pedidos:
        pedidos_formatados.append({
            'servico_nome': p.servico.nome,
            'nome_morador': getattr(p.usuario, 'perfil', None) == 'morador' and p.usuario.email or None,
            'usuario_email': p.usuario.email,
            'status': p.status,
            'data_solicitacao': p.data.replace(tzinfo=ZoneInfo("UTC")).astimezone(brasil).strftime('%d/%m/%Y %H:%M') if p.data else None,
            'observacao': p.observacao
        })

    servicos_disponiveis = Servico.query.order_by(Servico.nome).all()
    
    voltar_endpoint = 'dashboard_sindico' if current_user.tipo == 'sindico' else 'dashboard_morador'

    return render_template(
        'meus_pedidos.html',
        pedidos=pedidos_formatados,
        servicos_disponiveis=servicos_disponiveis,
        voltar_endpoint=voltar_endpoint
    )

@app.route('/pedidos')
@tipo_requerido('sindico')
def pedidos():
    servico_filtro = request.args.get('servico')
    
    query = Pedido.query  # Todos os pedidos
    
    if servico_filtro and servico_filtro.isdigit():
        query = query.filter_by(servico_id=int(servico_filtro))
    
    pedidos = query.order_by(Pedido.data.desc()).all()
    
    pedidos_formatados = []
    for p in pedidos:
        pedidos_formatados.append({
            'servico_nome': p.servico.nome,
            'nome_morador': p.usuario.email,  # sempre mostrar email do morador
            'usuario_email': p.usuario.email,
            'status': p.status,
            'data_solicitacao': p.data.replace(tzinfo=ZoneInfo("UTC")).astimezone(brasil).strftime('%d/%m/%Y %H:%M') if p.data else None,
            'observacao': p.observacao
        })

    servicos_disponiveis = Servico.query.order_by(Servico.nome).all()
    
    return render_template(
        'pedidos.html',
        pedidos=pedidos_formatados,
        servicos_disponiveis=servicos_disponiveis,
        voltar_endpoint='dashboard_sindico'
    )


from flask import render_template
from app import app
from models import Pedido, Usuario

@app.route('/historico')
@tipo_requerido('sindico')
def historico():
    # Buscar todos os pedidos (ou com filtros, se houver)
    pedidos = Pedido.query.order_by(Pedido.data.desc()).all()

    pedidos_formatados = []
    for p in pedidos:
        pedidos_formatados.append({
            'id': p.id,  # necessário para o dropdown de alteração
            'servico_nome': p.servico.nome,
            'nome_morador': getattr(p.usuario, 'perfil', None) == 'morador' and p.usuario.email or None,
            'usuario_email': p.usuario.email,
            'status': p.status,
            'data_solicitacao': p.data.replace(tzinfo=ZoneInfo("UTC")).astimezone(brasil).strftime('%d/%m/%Y %H:%M') if p.data else None,
            'observacao': p.observacao
        })

    return render_template(
        'historico.html',
        pedidos=pedidos_formatados
    )

@app.route('/alterar_status/<int:pedido_id>', methods=['POST'])
@login_required
def alterar_status(pedido_id):
    if current_user.tipo != 'sindico':
        flash("Acesso negado.", "danger")
        return redirect(url_for('historico'))

    novo_status = request.form.get('status')
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.status = novo_status
    db.session.commit()

    flash(f"Status do pedido atualizado para '{novo_status}'.", "success")
    return redirect(url_for('historico'))

@app.route('/gerenciar_sindico')
def gerenciar_sindico():
    # Recupera todos os usuários e serviços disponíveis
    usuarios = Usuario.query.all()
    servicos_disponiveis = Servico.query.all()
    return render_template('gerenciar_sindico.html', usuarios=usuarios, servicos_disponiveis=servicos_disponiveis)

# Promover morador a síndico
@app.route('/promover_sindico/<int:morador_id>', methods=['POST'])
def promover_sindico(morador_id):
    morador = Usuario.query.get_or_404(morador_id)
    # Rebaixa o síndico atual, se houver
    sindico_atual = Usuario.query.filter_by(tipo='sindico').first()
    if sindico_atual:
        sindico_atual.tipo = 'morador'
        sindico_atual.perfil = 'morador'
    
    # Promove o morador selecionado
    morador.tipo = 'sindico'
    morador.perfil = 'sindico'
    db.session.commit()
    flash(f"{morador.email} foi promovido a síndico!", "success")
    return redirect(url_for('gerenciar_sindico'))

# Rebaixar síndico para morador
@app.route('/dispromover_sindico/<int:morador_id>', methods=['POST'])
def dispromover_sindico(morador_id):
    usuario = Usuario.query.get_or_404(morador_id)
    if usuario.tipo == 'sindico':
        usuario.tipo = 'morador'
        usuario.perfil = 'morador'
        db.session.commit()
        flash(f"{usuario.email} foi rebaixado para morador.", "success")
    else:
        flash("Este usuário não é síndico.", "warning")
    return redirect(url_for('gerenciar_sindico'))




# -------------------------------
# DASHBOARD MORADOR
# -------------------------------
@app.route('/dashboard_morador')
@tipo_requerido('morador')
def dashboard_morador():
    # O decorador já garante que apenas moradores acessam
    return render_template('dashboard_morador.html', morador=current_user)

# -------------------------------
# DASHBOARD SÍNDICO
# -------------------------------
@app.route('/dashboard_sindico')
@tipo_requerido('sindico')
def dashboard_sindico():
    # Consulta serviços e status dos pedidos
    query_result = db.session.query(Servico.nome, db.func.count(Pedido.id))\
        .join(Pedido, isouter=True).group_by(Servico.id).all()
    servicos_count = [{'nome': nome, 'quantidade': quantidade} for nome, quantidade in query_result]
    status_count = db.session.query(Pedido.status, db.func.count(Pedido.id)).group_by(Pedido.status).all()
    return render_template('dashboard_sindico.html', servicos_count=servicos_count, status_count=status_count)



# -------------------------------
# EXECUÇÃO DO APP
# -------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
