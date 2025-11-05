import sqlite3

conn = sqlite3.connect('solicitacoes.db')
cursor = conn.cursor()

# Apaga pedidos antigos
cursor.execute("DELETE FROM pedidos")

# Apaga serviços antigos
cursor.execute("DELETE FROM servicos")

# (Opcional) Apaga usuários de teste, mantendo o síndico principal
# cursor.execute("DELETE FROM usuarios WHERE tipo='morador'")

conn.commit()
conn.close()

print("Dados antigos apagados. Banco e tabelas permanecem intactos.")

