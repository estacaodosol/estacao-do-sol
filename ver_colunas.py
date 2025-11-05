import sqlite3

# Conecta ao banco (cria se não existir)
conn = sqlite3.connect('condominio.db')
c = conn.cursor()

# Cria a tabela servicos se não existir
c.execute('''
CREATE TABLE IF NOT EXISTS servicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT UNIQUE NOT NULL
)
''')

# Verifica se a tabela existe e mostra colunas
c.execute("PRAGMA table_info(servicos)")
colunas = c.fetchall()
print("Estrutura da tabela 'servicos':")
for col in colunas:
    print(col)

conn.commit()
conn.close()
