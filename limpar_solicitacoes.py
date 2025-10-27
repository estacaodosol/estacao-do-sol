import sqlite3

conn = sqlite3.connect('solicitacoes.db')
cursor = conn.cursor()

cursor.execute("DELETE FROM solicitacoes")
conn.commit()
conn.close()

print("Todas as solicitações foram apagadas com sucesso.")
