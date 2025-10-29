import sqlite3
import os

# Caminho do banco de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'solicitacoes.db')

def criar_tabelas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Cria a tabela 'usuarios' se não existir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL
        );
    ''')

    # Cria a tabela 'solicitacoes' se não existir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS solicitacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            nome TEXT NOT NULL,
            servico TEXT NOT NULL,
            descricao TEXT,
            data TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendente',
            observacao TEXT
        );
    ''')

    conn.commit()
    print("✅ Tabelas criadas ou já existiam.")
    conn.close()

def verificar_estrutura():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n--- Estrutura da tabela 'usuarios' ---")
    cursor.execute("PRAGMA table_info(usuarios);")
    for coluna in cursor.fetchall():
        print(coluna)

    print("\n--- Estrutura da tabela 'solicitacoes' ---")
    cursor.execute("PRAGMA table_info(solicitacoes);")
    for coluna in cursor.fetchall():
        print(coluna)

    conn.close()

if __name__ == "__main__":
    criar_tabelas()
    verificar_estrutura()
