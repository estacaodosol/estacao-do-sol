from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from functools import wraps

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'

DATABASE = 'solicitacoes.db'

# -------------------------------
# Funções auxiliares
# -------------------------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_requerido(tipo=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                return redirect(url_for('login'))
            if tipo:
                conn = get_db_connection()
                usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', 
                                       (session['usuario_id'],)).fetchone()
                conn.close()
                if not usuario or usuario['tipo'] != tipo:
                    return "Acesso negado!"
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def criar_sindico_inicial():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE tipo = 'sindico'")
    existe = cursor.fetchone()
    if not existe:
        cursor.execute(
            "INSERT INTO usuarios (email, senha, tipo) VALUES (?, ?, ?)",
            ('sindico@condominio.com', 'senha123', 'sindico')
        )
        conn.commit()
        print("✅ Síndico inicial criado: sindico@condominio.com / senha123")
    conn.close()

# -------------------------------
# Rotas
# -------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        conn = get_db_connection()
        usuario = conn.execute('SELECT * FROM usuarios WHERE email = ? AND senha = ?', 
                               (email, senha)).fetchone()
        conn.close()
        if usuario:
            session['usuario_id'] = usuario['id']
            if usuario['tipo'] == 'sindico':
                return redirect(url_for('gerenciar_sindico'))
            else:
                return redirect(url_for('index'))
        else:
            erro = 'Email ou senha inválidos!'
    return render_template('login.html', erro=erro)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    erro = None
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        conn = get_db_connection()
        existente = conn.execute('SELECT * FROM usuarios WHERE email = ?', 
                                 (email,)).fetchone()
        if existente:
            erro = 'Email já cadastrado!'
        else:
            conn.execute('INSERT INTO usuarios (email, senha, tipo) VALUES (?, ?, ?)',
                         (email, senha, 'morador'))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        conn.close()
    return render_template('cadastro.html', erro=erro)

@app.route('/gerenciar_sindico', methods=['GET', 'POST'])
@login_requerido('sindico')
def gerenciar_sindico():
    conn = get_db_connection()
    if request.method == 'POST':
        novo_sindico_email = request.form['email']
        # Atualiza todos os síndicos existentes para morador
        conn.execute("UPDATE usuarios SET tipo='morador' WHERE tipo='sindico'")
        # Seta novo síndico
        conn.execute("UPDATE usuarios SET tipo='sindico' WHERE email=?", 
                     (novo_sindico_email,))
        conn.commit()
        return redirect(url_for('gerenciar_sindico'))
    moradores = conn.execute("SELECT * FROM usuarios WHERE tipo='morador'").fetchall()
    conn.close()
    return render_template('gerenciar_sindico.html', moradores=moradores)

# -------------------------------
# Inicialização
# -------------------------------
if __name__ == '__main__':
    criar_sindico_inicial()
    app.run(debug=True)
