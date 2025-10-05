# models/models.py

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# --- MODELO DE DADOS (Tabela Session) ---
class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(80), nullable=False)
    exercise_name = db.Column(db.String(120), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration_seconds = db.Column(db.Float)
    smoothness_score = db.Column(db.Float)
    data_file_path = db.Column(db.String(255)) 
    
    # Colunas para Máximos (ROM/Ângulo) e para Jogo (Score)
    max_rom = db.Column(db.Float)
    max_angle = db.Column(db.Float)
    game_score = db.Column(db.Integer, default=0) # Nova coluna para pontuação do jogo

    def __repr__(self):
        return f'<Session {self.id} - {self.patient_id}>'