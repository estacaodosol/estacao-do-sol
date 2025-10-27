import sqlite3

conn = sqlite3.connect('solicitacoes.db')
cursor = conn.cursor()

cursor.execute('SELECT * FROM solicitacoes')
dados = cursor.fetchall()

conn.close()

for linha in dados:
    print(linha)
