import sqlite3

conn = sqlite3.connect('solicitacoes.db')
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(solicitacoes)")
colunas = cursor.fetchall()

conn.close()

for coluna in colunas:
    print(f"Nome: {coluna[1]} | Tipo: {coluna[2]}")
