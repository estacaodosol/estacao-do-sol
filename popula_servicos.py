import sqlite3

# Conecta ao banco
conn = sqlite3.connect('solicitacoes.db')
cursor = conn.cursor()

# Cria tabela de serviços (se não existir)
cursor.execute('''
CREATE TABLE IF NOT EXISTS servicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL
)
''')

# Insere serviços iniciais
servicos = ['Elétrica', 'Hidráulica', 'Jardinagem', 'Elevador', 'Segurança']
for s in servicos:
    cursor.execute('INSERT OR IGNORE INTO servicos (nome) VALUES (?)', (s,))

conn.commit()
conn.close()
print("Serviços inseridos com sucesso!")
