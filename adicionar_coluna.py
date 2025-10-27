import sqlite3

conn = sqlite3.connect('solicitacoes.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE solicitacoes ADD COLUMN observacao TEXT")
    print("Coluna 'observacao' adicionada com sucesso.")
except sqlite3.OperationalError as e:
    print("Erro:", e)

conn.commit()
conn.close()
