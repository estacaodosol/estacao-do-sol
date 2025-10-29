import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, Response
from functools import wraps
from datetime import datetime
import csv

app = Flask(__name__)
app.secret_key = 'chave-secreta'

# Caminho fixo para o banco de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'solicitacoes.db')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Decorador para exigir login e tipo de usuário
def login_requerido(tipo=None):
    def decorador(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'usuario' not in session:
                return redirect(url_for('login'))

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT tipo FROM usuarios WHERE email = ?", (session['usuario'],))
            usuario_db = cursor.fetchone()
            conn.close()

            if not usuario_db:
                session.clear()
                return redirect(url_for('login'))

            session['tipo'] = usuario_db['tipo'].strip().lower()

            if tipo and session.get('tipo') != tipo.lower():
                return redirect(url_for('inicio'))

            return func(*args, **kwargs)
        return wrapper
    return decorador


# Criação do síndico inicial
def criar_sindico_inicial():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE tipo = 'sindico'")
    existe = cursor.fetchone()
    if not existe:
        cursor.execute("INSERT INTO usuarios (email, senha, tipo) VALUES (?, ?, ?)",
                       ('sindico@condominio.com', 'senha123', 'sindico'))
        conn.commit()
        print("✅ Síndico inicial criado: sindico@condominio.com / senha123")
    conn.close()


# Antes de cada requisição, atualiza tipo de usuário da sessão
@app.before_request
def verificar_sindico():
    if 'usuario' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT tipo FROM usuarios WHERE email = ?", (session['usuario'],))
        usuario_db = cursor.fetchone()
        conn.close()

        if usuario_db:
            tipo_atual = usuario_db['tipo'].strip().lower()
            tipo_sessao = session.get('tipo', '').lower()

            if tipo_atual != tipo_sessao:
                session['tipo'] = tipo_atual
                if tipo_atual == 'sindico':
                    session['aviso_sindico'] = "✅ Agora você é síndico e tem acesso às funcionalidades administrativas."
                else:
                    session['aviso_sindico'] = "⚠️ Seus privilégios de síndico foram removidos."
        else:
            session.clear()


# Página inicial
@app.route('/')
def inicio():
    return render_template('inicio.html')


# Página de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (email, senha))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            session['usuario'] = usuario['email']
            session['tipo'] = usuario['tipo'].strip().lower()

            if session['tipo'] == 'sindico':
                return redirect(url_for('historico'))
            else:
                return redirect(url_for('meus_pedidos'))
        else:
            erro = 'E-mail ou senha inválidos.'

    return render_template('login.html', erro=erro)


# Página de cadastro (apenas morador)
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    erro = None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE tipo = 'sindico'")
    existe_sindico = cursor.fetchone()
    conn.close()

    if existe_sindico:
        if request.method == 'POST':
            email = request.form['email']
            senha = request.form['senha']
            tipo = 'morador'

            if not email or not senha:
                erro = 'Todos os campos são obrigatórios.'
            else:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
                existente = cursor.fetchone()

                if existente:
                    erro = 'E-mail já cadastrado.'
                else:
                    cursor.execute("INSERT INTO usuarios (email, senha, tipo) VALUES (?, ?, ?)",
                                   (email, senha, tipo))
                    conn.commit()
                    conn.close()
                    return redirect(url_for('login'))

                conn.close()
        return render_template('cadastro.html', erro=erro)
    else:
        # Se não existe síndico, força criar o primeiro síndico
        return redirect(url_for('login'))


# Formulário de solicitações
@app.route('/formulario', methods=['GET', 'POST'])
@login_requerido()
def formulario():
    if request.method == 'POST':
        usuario = session.get('usuario')
        nome = request.form['nome']
        servico = request.form['servico']
        descricao = request.form['descricao']
        status = 'pendente'
        data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO solicitacoes (usuario, nome, servico, descricao, data, status)
                          VALUES (?, ?, ?, ?, ?, ?)''', (usuario, nome, servico, descricao, data, status))
        conn.commit()
        conn.close()

        session['nova_solicitacao'] = True
        return redirect(url_for('inicio'))

    return render_template('formulario.html')


# Histórico de solicitações
@app.route('/historico', methods=['GET', 'POST'])
@login_requerido()
def historico():
    usuario = session.get('usuario')
    tipo = session.get('tipo', '').strip().lower()

    nome = request.args.get('nome', '')
    servico = request.args.get('servico', '')
    status = request.args.get('status', '')
    data_inicial = request.args.get('data_inicial', '')
    data_final = request.args.get('data_final', '')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT servico FROM solicitacoes WHERE servico IS NOT NULL ORDER BY servico')
    servicos_disponiveis = [row['servico'] for row in cursor.fetchall()]

    query = "SELECT * FROM solicitacoes WHERE 1=1"
    params = []

    if tipo == 'morador':
        query += " AND usuario = ?"
        params.append(usuario)
    if nome:
        query += " AND nome LIKE ?"
        params.append(f"%{nome}%")
    if servico:
        query += " AND servico LIKE ?"
        params.append(f"%{servico}%")
    if status:
        query += " AND status = ?"
        params.append(status)
    if data_inicial:
        query += " AND date(data) >= date(?)"
        params.append(data_inicial)
    if data_final:
        query += " AND date(data) <= date(?)"
        params.append(data_final)

    query += " ORDER BY data DESC"
    cursor.execute(query, params)
    solicitacoes = cursor.fetchall()
    conn.close()

    return render_template('historico.html',
                           solicitacoes=solicitacoes,
                           tipo=tipo,
                           servicos_disponiveis=servicos_disponiveis)


# Meus pedidos (moradores)
@app.route('/meus_pedidos')
@login_requerido()
def meus_pedidos():
    usuario = session.get('usuario')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM solicitacoes WHERE usuario = ? ORDER BY data DESC", (usuario,))
    pedidos = cursor.fetchall()
    conn.close()
    return render_template('meus_pedidos.html', pedidos=pedidos)


# Alterar status (sindico)
@app.route('/alterar_status', methods=['POST'])
@login_requerido('sindico')
def alterar_status():
    id = request.form['id']
    novo_status = request.form['status']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE solicitacoes SET status = ? WHERE id = ?', (novo_status, id))
    conn.commit()
    conn.close()

    return redirect(url_for('historico'))


# Página para gerenciar síndico
@app.route('/gerenciar_sindico', methods=['GET', 'POST'])
@login_requerido('sindico')
def gerenciar_sindico():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        novo_sindico_email = request.form.get('novo_sindico')
        if novo_sindico_email:
            cursor.execute("UPDATE usuarios SET tipo = 'morador' WHERE tipo = 'sindico'")
            cursor.execute("UPDATE usuarios SET tipo = 'sindico' WHERE email = ?", (novo_sindico_email,))
            conn.commit()
            conn.close()
            return redirect(url_for('gerenciar_sindico'))

    cursor.execute("SELECT email FROM usuarios WHERE tipo != 'sindico'")
    usuarios = cursor.fetchall()
    conn.close()
    return render_template('gerenciar_sindico.html', usuarios=usuarios)


# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    criar_sindico_inicial()
    app.run(debug=True)
