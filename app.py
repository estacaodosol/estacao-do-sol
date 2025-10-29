from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps
import os
import bcrypt

# -------------------------------
# Configuração básica
# -------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "devkey")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # True em produção com HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

DATABASE = 'solicitacoes.db'

# -------------------------------
# Funções auxiliares
# -------------------------------
def get_db_connection():
    """Retorna uma conexão com o banco de dados SQLite."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_requerido(tipo=None):
    """Decorator para proteger rotas que exigem login e/ou tipo de usuário."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                flash("Faça login para acessar esta página.", "warning")
                return redirect(url_for('login'))
            if tipo:
                with get_db_connection() as conn:
                    usuario = conn.execute(
                        'SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)
                    ).fetchone()
                if not usuario or usuario['tipo'] != tipo:
                    flash("Acesso negado.", "danger")
                    return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def criar_sindico_inicial():
    """Cria um síndico padrão se não houver nenhum cadastrado."""
    with get_db_connection() as conn:
        existe = conn.execute("SELECT * FROM usuarios WHERE tipo = 'sindico'").fetchone()
        if not existe:
            senha_hash = bcrypt.hashpw('senha123'.encode(), bcrypt.gensalt()).decode()
            conn.execute(
                "INSERT INTO usuarios (email, senha, tipo) VALUES (?, ?, ?)",
                ('sindico@condominio.com', senha_hash, 'sindico')
            )
            conn.commit()
            print("✅ Síndico inicial criado: sindico@condominio.com / senha123")

# -------------------------------
# Rotas principais
# -------------------------------
@app.route('/', endpoint='index')
@login_requerido()
def index():
    """Página inicial: mostra home se logado."""
    if session.get('usuario_tipo') == 'sindico':
        return redirect(url_for('gerenciar_sindico'))
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Tela de login com verificação de senha com hash e feedback de erros."""
    if 'usuario_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        with get_db_connection() as conn:
            usuario = conn.execute(
                'SELECT * FROM usuarios WHERE email = ?', (email,)
            ).fetchone()

        if usuario and bcrypt.checkpw(senha.encode(), usuario['senha'].encode()):
            session['usuario_id'] = usuario['id']
            session['usuario_tipo'] = usuario['tipo']
            flash("Login realizado com sucesso!", "success")

            if usuario['tipo'] == 'sindico':
                return redirect(url_for('gerenciar_sindico'))
            return redirect(url_for('index'))
        else:
            flash("Email ou senha inválidos!", "danger")

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Finaliza a sessão do usuário."""
    session.clear()
    flash("Você saiu da conta.", "info")
    return redirect(url_for('login'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    """Tela de cadastro de novos usuários."""
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        with get_db_connection() as conn:
            existente = conn.execute(
                'SELECT * FROM usuarios WHERE email = ?', (email,)
            ).fetchone()

            if existente:
                flash("Email já cadastrado!", "warning")
            else:
                senha_hash = bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()
                conn.execute(
                    'INSERT INTO usuarios (email, senha, tipo) VALUES (?, ?, ?)',
                    (email, senha_hash, 'morador')
                )
                conn.commit()
                flash("Cadastro realizado com sucesso! Faça login.", "success")
                return redirect(url_for('login'))

    return render_template('cadastro.html')

@app.route('/gerenciar_sindico', methods=['GET', 'POST'])
@login_requerido('sindico')
def gerenciar_sindico():
    """Área exclusiva do síndico para promover outro usuário."""
    with get_db_connection() as conn:
        if request.method == 'POST':
            novo_sindico_email = request.form['email']
            conn.execute("UPDATE usuarios SET tipo='morador' WHERE tipo='sindico'")
            conn.execute(
                "UPDATE usuarios SET tipo='sindico' WHERE email=?", (novo_sindico_email,)
            )
            conn.commit()
            flash("Síndico atualizado com sucesso!", "success")
            return redirect(url_for('gerenciar_sindico'))

        moradores = conn.execute(
            "SELECT * FROM usuarios WHERE tipo='morador'"
        ).fetchall()

    return render_template('gerenciar_sindico.html', moradores=moradores)

# -------------------------------
# Inicialização
# -------------------------------
if __name__ == '__main__':
    criar_sindico_inicial()
    app.run(debug=True)
