import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
# ATUALIZADO: Importações de módulos/pacotes
from config import SQLALCHEMY_DATABASE_URI
from models import db
from routes import main_bp
from camera_module import setup_mediapipe

# --- Configuração Inicial ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa o SQLAlchemy com o app
db.init_app(app)

# --- Registro de Blueprints (Rotas) ---
app.register_blueprint(main_bp)

# --- Configuração de Ferramentas (MediaPipe) ---
# MediaPipe 'hands' é um objeto que precisa ser inicializado
setup_mediapipe()

# --- Execução e Setup do Banco de Dados ---
if __name__ == '__main__':
    os.makedirs('static/data/sessions', exist_ok=True)
    
    with app.app_context():
        # Cria as tabelas (importante: apague 'fisioterapia_data.db' para aplicar novas colunas)
        db.create_all() 
    
    # Executa o servidor Flask
    app.run(debug=True, port=5000)
