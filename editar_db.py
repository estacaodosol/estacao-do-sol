import sqlite3

# Conecta no banco
conn = sqlite3.connect('solicitacoes.db')
cursor = conn.cursor()

# Exibe os registros atuais
print("Registros antes da alteração:")
for row in cursor.execute("SELECT id, servico FROM pedidos"):
    print(row)

# Atualiza registros com 'manutenção elétrica' para 'Elétrica'
cursor.execute("UPDATE pedidos SET servico = 'Elétrica' WHERE servico LIKE '%elétrica%'")

# Salva alterações
conn.commit()

# Exibe registros atualizados
print("\nRegistros depois da alteração:")
for row in cursor.execute("SELECT id, servico FROM pedidos"):
    print(row)

conn.close()
