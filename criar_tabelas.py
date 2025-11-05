# criar_tabelas.py
from app import db, app, Usuario
from flask_bcrypt import Bcrypt

# Inicializa o bcrypt
bcrypt = Bcrypt()

with app.app_context():
    # Cria todas as tabelas
    db.create_all()
    print("Tabelas criadas com sucesso!")

    # Verifica se o admin já existe
    if not Usuario.query.filter_by(email='admin@teste.com').first():
        # Cria senha criptografada
        senha_hash = bcrypt.generate_password_hash('admin123').decode('utf-8')
        admin = Usuario(email='admin@teste.com', senha=senha_hash, tipo='sindico')
        db.session.add(admin)
        db.session.commit()
        print("Admin criado com sucesso! Email: admin@teste.com | Senha: admin123")
    else:
        print("Admin já existe.")
