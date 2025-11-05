# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from functools import wraps
from werkzeug.utils import secure_filename
import pytz
from datetime import datetime

# -------------------------------
# Configuração do app
# -------------------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///condominio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'uma_chave_temporaria')

# Configuração de upload de arquivos
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Extensões
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Fusos horários
utc = pytz.utc
brasil = pytz.timezone('America/Sao_Paulo')

# -------------------------------
# MODELOS
# -------------------------------
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(128), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    pedidos = db.relationship('Pedido', backref='usuario', lazy=True)

class Morador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    apartamento = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

class Servico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    pedidos = db.relationship('Pedido', backref='servico', lazy=True)

    def __repr__(self):
        return f"{self.nome}"

class Pedido(db.Model):
    __tablename__ = 'pedido'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    servico_id = db.Column(db.Integer, db.ForeignKey('servico.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    foto = db.Column(db.String(200))  # caminho da imagem opcional
    status = db.Column(db.String(20), default='Pendente')
    observacao = db.Column(db.Text)
    data = db.Column(db.DateTime, default=datetime.utcnow)  # horário do pedido

    def __repr__(self):
        return f'<Pedido {self.id} - {self.nome}>'

# Cria as tabelas
with app.app_context():
    db.create_all()

# -------------------------------
# DECORADOR DE LOGIN
# -------------------------------
def login_requerido(tipo=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                flash('Você precisa estar logado.', 'warning')
                return redirect(url_for('login'))
            if tipo and session.get('tipo') != tipo:
                flash('Acesso não autorizado.', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# -------------------------------
# ROTAS DE AUTENTICAÇÃO
# -------------------------------
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and bcrypt.check_password_hash(usuario.senha, senha):
            session['usuario_id'] = usuario.id
            session['tipo'] = usuario.tipo
            if usuario.tipo == 'morador':
                return redirect(url_for('meus_pedidos'))
            else:
                return redirect(url_for('historico'))
        else:
            flash('Email ou senha incorretos.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu com sucesso.', 'success')
    return redirect(url_for('login'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        tipo = 'morador'

        if Usuario.query.filter_by(email=email).first():
            flash('Email já cadastrado.', 'warning')
            return redirect(url_for('cadastro'))

        hashed_senha = bcrypt.generate_password_hash(senha).decode('utf-8')
        novo_usuario = Usuario(email=email, senha=hashed_senha, tipo=tipo)
        db.session.add(novo_usuario)
        db.session.commit()

        flash('Cadastro realizado com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))

    return render_template('cadastro.html')

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
@login_requerido('morador')
def novo_pedido():
    servicos_disponiveis = Servico.query.order_by(Servico.nome).all()
    if not servicos_disponiveis:
        flash('Nenhum serviço disponível. Contate o síndico para cadastrar serviços.', 'warning')
        return redirect(url_for('meus_pedidos'))

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        servico_id = request.form.get('servico')
        usuario_id = session['usuario_id']

        if not nome or not servico_id:
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('novo_pedido'))

        servico = Servico.query.get(int(servico_id))
        if not servico:
            flash('Serviço inválido.', 'danger')
            return redirect(url_for('novo_pedido'))

        # ----- Upload de foto -----
        foto_arquivo = request.files.get('foto')
        caminho_foto = None
        if foto_arquivo and foto_arquivo.filename != '':
            import uuid
            ext = os.path.splitext(foto_arquivo.filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                flash('Formato de imagem não permitido. Use jpg, jpeg, png ou gif.', 'danger')
                return redirect(url_for('novo_pedido'))
            nome_arquivo = f"{uuid.uuid4().hex}{ext}"
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo)
            foto_arquivo.save(caminho_foto)
            caminho_foto = f"/{caminho_foto.replace(os.sep, '/')}"

        novo_pedido = Pedido(
            usuario_id=usuario_id,
            servico_id=servico.id,
            nome=nome,
            descricao=descricao,
            foto=caminho_foto
        )
        db.session.add(novo_pedido)
        db.session.commit()
        flash('Pedido cadastrado com sucesso!', 'success')
        return redirect(url_for('meus_pedidos'))

    return render_template('novo_pedido.html', servicos_disponiveis=servicos_disponiveis)

@app.route('/meus_pedidos')
@login_requerido('morador')
def meus_pedidos():
    usuario_id = session['usuario_id']
    servico_filtro = request.args.get('servico')

    query = Pedido.query.filter_by(usuario_id=usuario_id)
    if servico_filtro:
        try:
            servico_id = int(servico_filtro)
            query = query.filter_by(servico_id=servico_id)
        except ValueError:
            flash('Serviço inválido.', 'warning')

    pedidos = query.order_by(Pedido.data.desc()).all()
    servicos_disponiveis = Servico.query.order_by(Servico.nome).all()

    # Determinar dashboard correto
    if session.get('perfil') == 'sindico':
        voltar_endpoint = 'dashboard_sindico'
    else:
        voltar_endpoint = 'meus_pedidos'  # ou outra rota de morador que exista

    return render_template(
        'meus_pedidos.html',
        pedidos=pedidos,
        servicos_disponiveis=servicos_disponiveis,
        brasil=brasil,
        voltar_endpoint=voltar_endpoint
    )


# -------------------------------
# DASHBOARD SÍNDICO
# -------------------------------
@app.route('/historico')
@login_requerido('sindico')
def historico():
    pedidos_raw = db.session.query(
        Pedido.id,
        Pedido.data.label('data_solicitacao'),
        Pedido.status,
        Pedido.observacao,
        Servico.nome.label('servico_nome'),
        Usuario.email.label('usuario_email')  # usando email em vez de nome
    ).join(Servico, Pedido.servico_id == Servico.id
    ).join(Usuario, Pedido.usuario_id == Usuario.id
    ).order_by(Pedido.data.desc()).all()

    # Ajustando os dados antes de enviar para o template
    pedidos = []
    for p in pedidos_raw:
        pedidos.append({
            "id": p.id,
            "data_solicitacao": p.data_solicitacao.strftime('%d/%m/%Y %H:%M') if p.data_solicitacao else "Não informada",
            "status": p.status or "",
            "observacao": p.observacao or "",
            "servico_nome": p.servico_nome or "",
            "usuario_email": p.usuario_email or ""
        })

    return render_template('historico.html', pedidos=pedidos)




@app.route('/dashboard_sindico')
@login_requerido('sindico')
def dashboard_sindico():
    # Consulta os serviços e a quantidade de pedidos por serviço
    query_result = db.session.query(
        Servico.nome, db.func.count(Pedido.id)
    ).join(Pedido, isouter=True).group_by(Servico.id).all()

    # Transformar em lista de dicionários
    servicos_count = [{'nome': nome, 'quantidade': quantidade} for nome, quantidade in query_result]

    # Contagem de status (se quiser usar)
    status_count = db.session.query(Pedido.status, db.func.count(Pedido.id)).group_by(Pedido.status).all()

    return render_template('dashboard_sindico.html',
                           servicos_count=servicos_count,
                           status_count=status_count)


# -------------------------------
# GERENCIAMENTO DE USUÁRIOS
# -------------------------------
@app.route('/gerenciar_sindico')
@login_requerido('sindico')
def gerenciar_sindico():
    usuarios = Usuario.query.all()
    servicos_disponiveis = Servico.query.all()
    return render_template('gerenciar_sindico.html', usuarios=usuarios, servicos_disponiveis=servicos_disponiveis)

@app.route('/promover_sindico/<int:morador_id>', methods=['POST'])
@login_requerido('sindico')
def promover_sindico(morador_id):
    novo = Usuario.query.get(morador_id)
    atual = Usuario.query.filter_by(tipo='sindico').first()
    if novo and atual:
        novo.tipo = 'sindico'
        atual.tipo = 'morador'
        db.session.commit()
        flash('Novo síndico promovido com sucesso!', 'success')
    else:
        flash('Não foi possível promover o síndico.', 'danger')
    return redirect(url_for('gerenciar_sindico'))

@app.route('/dispromover_sindico/<int:morador_id>', methods=['POST'])
@login_requerido('sindico')
def dispromover_sindico(morador_id):
    usuario = Usuario.query.get(morador_id)
    if usuario and usuario.tipo == 'sindico':
        usuario.tipo = 'morador'
        db.session.commit()
        flash(f"{usuario.email} foi rebaixado a morador.", 'info')
    else:
        flash('Usuário não encontrado ou já é morador.', 'warning')
    return redirect(url_for('gerenciar_sindico'))


# -------------------------------
# ATUALIZAÇÃO DE STATUS DE PEDIDO
# -------------------------------
@app.route('/atualizar_status/<int:pedido_id>', methods=['POST'])
@login_requerido('sindico')
def atualizar_status(pedido_id):
    pedido = Pedido.query.get(pedido_id)
    novo_status = request.form.get('status')
    observacao = request.form.get('observacao', '').strip()

    if pedido and novo_status in ['Pendente', 'Em andamento', 'Concluído']:
        pedido.status = novo_status
        pedido.observacao = observacao
        db.session.commit()
        flash('Status do pedido atualizado!', 'success')
    else:
        flash('Não foi possível atualizar o status.', 'danger')

    return redirect(url_for('historico'))

# -------------------------------
# EXECUÇÃO DO APP
# -------------------------------
if __name__ == '__main__':
    app.run(debug=True)
