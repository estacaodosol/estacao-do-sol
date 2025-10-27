import sqlite3

conn = sqlite3.connect('solicitacoes.db')
cursor = conn.cursor()

# Adiciona a coluna 'status' se ela ainda não existir
try:
    cursor.execute("ALTER TABLE solicitacoes ADD COLUMN status TEXT")
    print("Coluna 'status' adicionada com sucesso.")
except sqlite3.OperationalError as e:
    print("Erro:", e)

conn.commit()
conn.close()
