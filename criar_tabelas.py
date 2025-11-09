from app import app, db
from models import Usuario, Morador, Apartamento, Servico, Pedido  # Todos os modelos importados
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

with app.app_context():
    # Cria todas as tabelas que ainda não existem
    db.create_all()
    print("Tabelas criadas com sucesso!")

    # Cria o admin se não existir
    if not Usuario.query.filter_by(email='admin@teste.com').first():
        senha_hash = bcrypt.generate_password_hash('admin123').decode('utf-8')
        admin = Usuario(
            email='admin@teste.com',
            senha=senha_hash,
            tipo='sindico',
            perfil='sindico'
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin criado com sucesso! Email: admin@teste.com | Senha: admin123")
    else:
        print("Admin já existe.")
