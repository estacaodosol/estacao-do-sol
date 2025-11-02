import os
import zipfile
from datetime import datetime

# Caminhos e nomes
projeto = os.getcwd()  # pasta atual do projeto
nome_projeto = "Condominio_App"
pasta_backup = r"C:\Users\jojun\Backups"  # destino do backup

# Data atual para o nome do arquivo
data_atual = datetime.now().strftime("%d-%m-%y_%H-%M-%S")
nome_arquivo = f"{nome_projeto}_{data_atual}.zip"
caminho_zip = os.path.join(pasta_backup, nome_arquivo)

# Criar a pasta de destino se não existir
os.makedirs(pasta_backup, exist_ok=True)

# Criar o arquivo ZIP
with zipfile.ZipFile(caminho_zip, "w", zipfile.ZIP_DEFLATED) as backup_zip:
    for raiz, _, arquivos in os.walk(projeto):
        # Ignorar venv, __pycache__ e a própria pasta de backup
        if "venv" in raiz or "__pycache__" in raiz or "Backups" in raiz:
            continue
        for arquivo in arquivos:
            caminho_completo = os.path.join(raiz, arquivo)
            caminho_relativo = os.path.relpath(caminho_completo, projeto)
            backup_zip.write(caminho_completo, caminho_relativo)

print(f"✅ Backup criado com sucesso em: {caminho_zip}")
