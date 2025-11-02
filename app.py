from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps
from datetime import datetime
from flask_bcrypt import Bcrypt  # Para criptografia de senha

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'
bcrypt = Bcrypt(app)

# Lista de serviços disponíveis
SERVICOS_DISPONIVEIS = ['Elétrica', 'Hidráulica', 'Jardinagem', 'Elevador']

# -------------------------------
# FUNÇÃO DE CONEXÃO COM BANCO
# -------------------------------
def get_db_connection():
    conn = sqlite3.connect('solicitacoes.db')  # banco correto
    conn.row_factory = sqlite3.Row
    return conn

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

@app.route('/')
def index():
    return redirect(url_for('login'))

# -------------------------------
# LOGIN
# -------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        conn = get_db_connection()
        usuario = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()
        conn.close()

        if usuario and bcrypt.check_password_hash(usuario['senha'], senha):
            session['usuario_id'] = usuario['id']
            session['tipo'] = usuario['tipo']

            if usuario['tipo'] == 'morador':
                return redirect(url_for('meus_pedidos'))
            elif usuario['tipo'] == 'sindico':
                return redirect(url_for('historico'))
        else:
            flash('Email ou senha incorretos.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# -------------------------------
# LOGOUT
# -------------------------------
@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu com sucesso.', 'success')
    return redirect(url_for('login'))

# -------------------------------
# CADASTRO
# -------------------------------
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        tipo = 'morador'  # sempre cadastra como morador

        # Criptografar senha
        hashed_senha = bcrypt.generate_password_hash(senha).decode('utf-8')

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO usuarios (email, senha, tipo) VALUES (?, ?, ?)',
            (email, hashed_senha, tipo)
        )
        conn.commit()
        conn.close()

        flash('Cadastro realizado com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))

    return render_template('cadastro.html')

# -------------------------------
# ROTA DO MORADOR - MEUS PEDIDOS
# -------------------------------
@app.route('/meus_pedidos')
@login_requerido('morador')
def meus_pedidos():
    usuario_id = session['usuario_id']
    servico_filtro = request.args.get('servico')

    conn = get_db_connection()
    query = """
        SELECT p.id, p.data, u.email as usuario, p.nome, p.servico, p.descricao, p.status, p.observacao
        FROM pedidos p
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.usuario_id = ?
    """
    params = [usuario_id]

    if servico_filtro:
        query += " AND p.servico = ?"
        params.append(servico_filtro)

    query += " ORDER BY p.data DESC"
    pedidos = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('meus_pedidos.html', pedidos=pedidos, servicos_disponiveis=SERVICOS_DISPONIVEIS)

from flask import render_template
from collections import Counter
#import datetime

SERVICOS_DISPONIVEIS = ['Elétrica', 'Hidráulica', 'Jardinagem', 'Segurança']

@app.route('/dashboard_sindico')
@login_requerido('sindico')
def dashboard_sindico():
    conn = get_db_connection()
    pedidos = [dict(p) for p in conn.execute('SELECT servico, status, data FROM pedidos').fetchall()]
    conn.close()

    # Padronizar os nomes e contar
    servicos_count = Counter(p['servico'].strip().capitalize() for p in pedidos)
    servicos_count_completo = {s: servicos_count.get(s, 0) for s in SERVICOS_DISPONIVEIS}

    status_count = Counter(p['status'] for p in pedidos)
    datas_count = Counter(p['data'] for p in pedidos)

    return render_template(
        'dashboard_sindico.html',
        servicos_count=servicos_count_completo,
        status_count=status_count,
        datas_count=datas_count
    )


# -------------------------------
# NOVO PEDIDO
# -------------------------------
@app.route('/novo_pedido', methods=['GET', 'POST'])
@login_requerido('morador')
def novo_pedido():
    if request.method == 'POST':
        nome = request.form['nome']
        servico = request.form['servico']
        descricao = request.form['descricao']
        usuario_id = session['usuario_id']
        data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = 'Pendente'

        # Validação do serviço
        if servico not in SERVICOS_DISPONIVEIS:
            flash('Serviço inválido.', 'danger')
            return redirect(url_for('novo_pedido'))

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO pedidos (usuario_id, nome, servico, descricao, status, data) VALUES (?, ?, ?, ?, ?, ?)',
            (usuario_id, nome, servico, descricao, status, data)
        )
        conn.commit()
        conn.close()

        flash('Pedido cadastrado com sucesso!', 'success')
        return redirect(url_for('meus_pedidos'))

    return render_template('novo_pedido.html', servicos_disponiveis=SERVICOS_DISPONIVEIS)

# -------------------------------
# ROTA DO SÍNDICO - HISTÓRICO
# -------------------------------
@app.route('/historico')
@login_requerido('sindico')
def historico():
    conn = get_db_connection()

    # Filtros
    nome_filtro = request.args.get('nome', '')
    servico_filtro = request.args.get('servico', '')
    status_filtro = request.args.get('status', '')
    data_inicial = request.args.get('data_inicial', '')
    data_final = request.args.get('data_final', '')

    query = """
        SELECT p.id, p.data, u.email as usuario, p.nome, p.servico, 
               p.descricao, p.status, p.observacao
        FROM pedidos p
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE 1=1
    """
    params = []

    if nome_filtro:
        query += " AND p.nome LIKE ?"
        params.append(f"%{nome_filtro}%")
    if servico_filtro:
        query += " AND p.servico = ?"
        params.append(servico_filtro)
    if status_filtro:
        query += " AND p.status = ?"
        params.append(status_filtro)
    if data_inicial:
        query += " AND p.data >= ?"
        params.append(data_inicial)
    if data_final:
        query += " AND p.data <= ?"
        params.append(data_final)

    query += " ORDER BY p.data DESC"

    solicitacoes = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('historico.html',
                           solicitacoes=solicitacoes,
                           servicos_disponiveis=SERVICOS_DISPONIVEIS,
                           tipo=session['tipo'])

# -------------------------------
# ALTERAR STATUS (SÓ SÍNDICO)
# -------------------------------
@app.route('/alterar_status', methods=['POST'])
@login_requerido('sindico')
def alterar_status():
    pedido_id = request.form['id']
    novo_status = request.form['status']

    conn = get_db_connection()
    conn.execute('UPDATE pedidos SET status = ? WHERE id = ?', (novo_status, pedido_id))
    conn.commit()
    conn.close()

    flash('Status atualizado com sucesso!', 'success')
    return redirect(url_for('historico'))

from flask import flash, redirect, url_for

# -------------------------------
# PROMOVER SÍNDICO
# -------------------------------
@app.route('/promover_sindico/<int:morador_id>', methods=['POST'])
@login_requerido('sindico')
def promover_sindico(morador_id):
    conn = get_db_connection()

    # Buscar síndico atual
    sindico_atual = conn.execute(
        "SELECT * FROM usuarios WHERE tipo = 'sindico'"
    ).fetchone()

    # Rebaixar síndico atual (se existir e for diferente do novo)
    if sindico_atual and sindico_atual['id'] != morador_id:
        conn.execute(
            "UPDATE usuarios SET tipo = 'morador' WHERE id = ?",
            (sindico_atual['id'],)
        )
        flash(f"O síndico {sindico_atual['email']} foi rebaixado a morador comum.", "info")

    # Promover o novo síndico
    conn.execute(
        "UPDATE usuarios SET tipo = 'sindico' WHERE id = ?",
        (morador_id,)
    )
    conn.commit()
    conn.close()

    flash("Novo síndico promovido com sucesso!", "success")
    return redirect(url_for('gerenciar_sindico'))


# -------------------------------
# DISPROMOVER SÍNDICO (REBAIXAR)
# -------------------------------
@app.route('/dispromover_sindico/<int:morador_id>', methods=['POST'])
@login_requerido('sindico')
def dispromover_sindico(morador_id):
    conn = get_db_connection()

    usuario = conn.execute(
        "SELECT * FROM usuarios WHERE id = ?", (morador_id,)
    ).fetchone()

    if usuario and usuario['tipo'] == 'sindico':
        conn.execute(
            "UPDATE usuarios SET tipo = 'morador' WHERE id = ?",
            (morador_id,)
        )
        conn.commit()
        flash(f"O síndico {usuario['email']} foi rebaixado a morador comum.", "info")
    else:
        flash("Usuário não encontrado ou já é morador.", "warning")

    conn.close()
    return redirect(url_for('gerenciar_sindico'))


# -------------------------------
# ROTA GERENCIAR SÍNDICO
# -------------------------------
@app.route('/gerenciar_sindico')
@login_requerido('sindico')
def gerenciar_sindico():
    conn = get_db_connection()

    # Buscar todos os usuários
    usuarios = conn.execute('SELECT id, email, tipo FROM usuarios').fetchall()

    # Estatísticas simples dos pedidos
    estatisticas = conn.execute(
        'SELECT servico, COUNT(*) as total FROM pedidos GROUP BY servico'
    ).fetchall()
    estatisticas_dict = {row['servico']: row['total'] for row in estatisticas}

    conn.close()

    return render_template(
        'gerenciar_sindico.html',
        usuarios=usuarios,
        estatisticas=estatisticas_dict
    )


# -------------------------------
# EXECUTAR APP
# -------------------------------
if __name__ == '__main__':
    app.run(debug=True)
