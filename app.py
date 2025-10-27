from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
from datetime import datetime
import csv
import os

app = Flask(__name__)
app.secret_key = 'chave-secreta'

# Decorador para exigir login e tipo de usuário
def login_requerido(tipo=None):
    def decorador(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'usuario' not in session:
                return redirect(url_for('login'))
            if tipo and session.get('tipo') != tipo:
                return redirect(url_for('inicio'))
            return func(*args, **kwargs)
        return wrapper
    return decorador

# Página inicial (visível para todos, com botões dinâmicos)
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

        conn = sqlite3.connect('solicitacoes.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (email, senha))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            session['usuario'] = usuario['email']
            session['tipo'] = usuario['tipo'].strip().lower()

            # Redireciona conforme o tipo de usuário
            if session['tipo'] == 'sindico':
                return redirect(url_for('historico'))
            else:
                return redirect(url_for('meus_pedidos'))  # Página do morador
        else:
            erro = 'E-mail ou senha inválidos.'

    return render_template('login.html', erro=erro)

@app.route('/alterar_status', methods=['POST'])
def alterar_status():
    if 'usuario' not in session or session.get('tipo', '').lower() != 'sindico':
        return redirect(url_for('login'))

    id = request.form['id']
    novo_status = request.form['status']

    conn = sqlite3.connect('solicitacoes.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE solicitacoes SET status = ? WHERE id = ?', (novo_status, id))
    conn.commit()
    conn.close()

    return redirect(url_for('historico'))


import sqlite3

# Conecta ao banco (cria se não existir)
conn = sqlite3.connect('solicitacoes.db')
cursor = conn.cursor()


# Página de cadastro
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    erro = None
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        tipo = request.form['tipo']

        if not email or not senha or not tipo:
            erro = 'Todos os campos são obrigatórios.'
        else:
            conn = sqlite3.connect('solicitacoes.db')
            cursor = conn.cursor()

            # Verifica se o e-mail já existe
            cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
            existente = cursor.fetchone()

            if existente:
                erro = 'E-mail já cadastrado.'
            else:
                cursor.execute("INSERT INTO usuarios (email, senha, tipo) VALUES (?, ?, ?)", (email, senha, tipo))
                conn.commit()
                conn.close()
                return redirect(url_for('login'))

            conn.close()

    return render_template('cadastro.html', erro=erro)


@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    if request.method == 'POST':
        usuario = session.get('usuario')
        nome = request.form['nome']
        servico = request.form['servico']
        descricao = request.form['descricao']
        status = 'pendente'  # Definido automaticamente
        data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = sqlite3.connect('solicitacoes.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO solicitacoes (usuario, nome, servico, descricao, data, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (usuario, nome, servico, descricao, data, status))
        conn.commit()
        conn.close()

        session['nova_solicitacao'] = True
        return redirect(url_for('inicio'))

    return render_template('formulario.html')


@app.route('/teste-salvar')
def teste_salvar():
    from datetime import datetime
    import sqlite3

    usuario = 'teste_morador'
    nome = 'Teste'
    servico = 'Limpeza'
    descricao = 'Teste de inserção no banco'
    data = datetime.now().strftime('%d/%m/%Y %H:%M')

    try:
        conn = sqlite3.connect('solicitacoes.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO solicitacoes (usuario, nome, servico, descricao, data)
            VALUES (?, ?, ?, ?, ?)
        ''', (usuario, nome, servico, descricao, data))
        conn.commit()
        conn.close()
        return '✅ Dados salvos com sucesso no banco!'
    except Exception as e:
        return f'❌ Erro ao salvar: {e}'
    
from flask import session, redirect, url_for, render_template
import sqlite3

from flask import session, redirect, url_for, render_template
import sqlite3

@app.route('/historico', methods=['GET', 'POST'])
@login_requerido()
def historico():
    import sqlite3
    from flask import session, request, render_template

    usuario = session.get('usuario')
    tipo = session.get('tipo', '').strip().lower()

    # Filtros recebidos via GET
    nome = request.args.get('nome', '')
    servico = request.args.get('servico', '')
    status = request.args.get('status', '')
    data_inicial = request.args.get('data_inicial', '')
    data_final = request.args.get('data_final', '')

    conn = sqlite3.connect('solicitacoes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Consulta para obter serviços disponíveis
    cursor.execute('SELECT DISTINCT servico FROM solicitacoes WHERE servico IS NOT NULL ORDER BY servico')
    servicos_disponiveis = [row['servico'] for row in cursor.fetchall()]

    # Monta a query dinâmica
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


@app.route('/listar')
@login_requerido()
def listar():
    import sqlite3
    from flask import request, render_template

    nome = request.args.get('nome', '')
    servico = request.args.get('servico', '')
    status = request.args.get('status', '')
    data_inicial = request.args.get('data_inicial', '')
    data_final = request.args.get('data_final', '')

    conn = sqlite3.connect('solicitacoes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM solicitacoes WHERE 1=1"
    params = []

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
    resultados = cursor.fetchall()
    conn.close()

    return render_template('listar.html', resultados=resultados)


@app.route('/estatisticas')
@login_requerido('sindico')
def estatisticas():
    import sqlite3

    conn = sqlite3.connect('solicitacoes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Contagem por tipo de serviço
    cursor.execute('SELECT servico, COUNT(*) FROM solicitacoes GROUP BY servico')
    servicos_raw = cursor.fetchall()
    servicos = {
        servico if servico is not None else 'Indefinido': quantidade
        for servico, quantidade in servicos_raw
    }

    # Contagem por status
    cursor.execute('SELECT status, COUNT(*) FROM solicitacoes GROUP BY status')
    status_raw = cursor.fetchall()
    status_contagem = {
        status if status is not None else 'Indefinido': quantidade
        for status, quantidade in status_raw
    }

    # Contagem por data
    cursor.execute('SELECT data, COUNT(*) FROM solicitacoes GROUP BY data ORDER BY data')
    data_raw = cursor.fetchall()
    por_data = {
        data if data is not None else 'Indefinido': quantidade
        for data, quantidade in data_raw
    }

    conn.close()

    return render_template('estatisticas.html',
                           servicos=servicos,
                           status_contagem=status_contagem,
                           por_data=por_data)

from flask import Response

@app.route('/exportar')
@login_requerido()
def exportar():
    import sqlite3
    import csv
    from io import StringIO
    from flask import request

    conn = sqlite3.connect('solicitacoes.db')
    cursor = conn.cursor()

    # Filtros (como na rota listar)
    nome = request.args.get('nome', '')
    servico = request.args.get('servico', '')
    status = request.args.get('status', '')
    data_inicial = request.args.get('data_inicial', '')
    data_final = request.args.get('data_final', '')

    query = "SELECT usuario, nome, servico, descricao, data, status FROM solicitacoes WHERE 1=1"
    params = []

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

    cursor.execute(query, params)
    resultados = cursor.fetchall()
    conn.close()

    # Gera CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Usuário', 'Nome', 'Serviço', 'Descrição', 'Data', 'Status'])
    for row in resultados:
        writer.writerow(row)

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=solicitacoes.csv"}
    )


@app.route('/meus_pedidos')
@login_requerido()
def meus_pedidos():
    import sqlite3
    from flask import session, render_template

    usuario = session.get('usuario')
    conn = sqlite3.connect('solicitacoes.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM solicitacoes WHERE usuario = ? ORDER BY data DESC", (usuario,))
    pedidos = cursor.fetchall()
    conn.close()

    return render_template('meus_pedidos.html', pedidos=pedidos)


@app.route('/atualizar_status/<int:id>', methods=['GET', 'POST'])
@login_requerido()
def atualizar_status(id):
    import sqlite3
    from flask import request, redirect, url_for, render_template

    conn = sqlite3.connect('solicitacoes.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        novo_status = request.form.get('status')
        observacao = request.form.get('observacao', '')
        cursor.execute("UPDATE solicitacoes SET status = ?, observacao = ? WHERE id = ?", (novo_status, observacao, id))
        conn.commit()
        conn.close()
        return redirect(url_for('listar'))

    cursor.execute("SELECT id, servico, descricao, status, usuario, nome, observacao FROM solicitacoes WHERE id = ?", (id,))
    solicitacao = cursor.fetchone()
    conn.close()
    return render_template('atualizar_status.html', solicitacao=solicitacao)

# Rota de logout
@app.route('/logout')
def logout():
    session.clear()  # Remove todos os dados da sessão
    return redirect(url_for('login'))  # Redireciona para a tela de login


# Executar o app
if __name__ == '__main__':
    app.run(debug=True)