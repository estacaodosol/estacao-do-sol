# utils.py
from functools import wraps
from flask import session, redirect, url_for, g
import sqlite3

def login_requerido(tipo_usuario):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                return redirect(url_for('login'))
            # você pode adicionar verificação de tipo aqui se quiser
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_db_connection():
    import sqlite3
    conn = sqlite3.connect('condominio.db')
    conn.row_factory = sqlite3.Row
    return conn
