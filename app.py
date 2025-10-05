# app.py

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
# Imports que refletem a nova estrutura modular
from config.config import SQLALCHEMY_DATABASE_URI
from models.models import db
from routes.routes import main_bp
from modules.camera_module import setup_mediapipe # Importa o setup de dentro de modules

# --- Configuração Inicial ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o SQLAlchemy com o app
db.init_app(app)

# --- Registro de Blueprints (Rotas) ---
app.register_blueprint(main_bp)

# --- Configuração de Ferramentas (MediaPipe) ---
setup_mediapipe()

# --- Execução e Setup do Banco de Dados ---
if __name__ == '__main__':
    # Cria os diretórios necessários
    os.makedirs('static/data/sessions', exist_ok=True)
    
    with app.app_context():
        # Cria as tabelas (apague 'fisioterapia_data.db' para aplicar novas colunas!)
        db.create_all() 
    
    app.run(debug=True, port=5000)