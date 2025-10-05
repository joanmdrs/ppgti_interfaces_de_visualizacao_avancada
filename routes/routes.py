# routes/routes.py

from flask import Blueprint, jsonify, render_template, send_file
from datetime import datetime
import json
import numpy as np
import os

# Imports que refletem a nova estrutura modular
from models.models import db, Session
from config.config import PATIENT_NAME
from modules.data_collector import DataCollector
from modules.metrics import calculate_smoothness

# Importa as variáveis e funções do módulo da câmera
import modules.camera_module as cam
from modules.camera_module import start_tracking_thread, stop_tracking_thread

# Cria um Blueprint para as rotas
main_bp = Blueprint('main', __name__)

# --- Funções Auxiliares ---
def carregar_exercicios():
    """Carrega a lista de exercícios do arquivo JSON."""
    try:
        with open('static/data/exercicios.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("[ERRO] Arquivo static/data/exercicios.json não encontrado.")
        return []

def load_exercise_by_id(exercise_id):
    """Retorna um exercício pelo ID."""
    exercicios_list = carregar_exercicios()
    return next((e for e in exercicios_list if e['id'] == exercise_id), None)

# --- Rota Principal ---

@main_bp.route('/')
def index():
    return render_template('home.html')

@main_bp.route('/exercicios')
def exercicios():
    exercicios_list = carregar_exercicios()
    return render_template('exercicios.html', exercicios=exercicios_list)

# --- Rotas de Início de Sessão ---

@main_bp.route('/start_exercise/<int:exercise_id>')
def start_exercise(exercise_id):
    """Inicia uma nova sessão de exercício STANDARD."""
    
    ex = load_exercise_by_id(exercise_id)
    if not ex or ex.get('type') != 'standard':
        return "Exercício padrão não encontrado ou tipo incorreto.", 404
    
    # 1. Configura parâmetros para o rastreio
    cam.CURRENT_ROM_MIN = ex.get('rom_min', 100)
    cam.CURRENT_ROM_MAX = ex.get('rom_max', 300)
    cam.CURRENT_METRIC_TYPE = ex.get('metrica', 'ROM (Distância)') 
    
    # NOVAS CONFIGURAÇÕES PARA LÓGICA DEDICADA E HOLD TIME
    cam.CURRENT_LOGIC_KEY = ex.get('logic_key', 'default') # Define a chave da função de renderização
    cam.HOLD_TIME_REQUIRED = ex.get('hold_time_seconds', 0.0)
    cam.HOLD_COMPLETE = False # Reseta o status de manutenção
    cam.HOLD_TIMER_START = 0.0 # Reseta o timer

    # 2. Configura estado
    safe_name = ex['titulo'].replace(' ', '_').replace('/', '_')
    cam.EXERCISE_NAME = safe_name
    cam.global_data_collector = DataCollector(patient_id=PATIENT_NAME, exercise_name=cam.EXERCISE_NAME)

    # 3. Inicia a thread de rastreio
    start_tracking_thread()
    
    return render_template('control_panel.html', 
                            patient=PATIENT_NAME.replace('_', ' '),
                            exercise=ex['titulo'])


@main_bp.route('/start_game/<int:exercise_id>')
def start_game(exercise_id):
    """Inicia uma nova sessão de exercício GAMIFICADO."""
    
    ex = load_exercise_by_id(exercise_id)
    if not ex or ex.get('type') != 'game':
        return "Jogo não encontrado ou tipo incorreto.", 404

    # 1. Configura parâmetros para o JOGO
    cam.CURRENT_LOGIC_KEY = ex.get('logic_key', 'target_hit_game') # Define a chave da função de renderização do jogo
    cam.GAME_SCORE = 0 # Zera a pontuação no início
    
    # 2. Configura estado
    safe_name = ex['titulo'].replace(' ', '_').replace('/', '_')
    cam.EXERCISE_NAME = safe_name
    cam.global_data_collector = DataCollector(patient_id=PATIENT_NAME, exercise_name=cam.EXERCISE_NAME)

    # 3. Inicia a thread de rastreio
    start_tracking_thread()

    # Retorna o template específico do jogo
    return render_template('game.html', 
                            patient=PATIENT_NAME.replace('_', ' '),
                            exercise=ex['titulo'])

# --- Rota de Parada de Sessão ---

@main_bp.route('/stop_session', methods=['POST'])
def stop_session():
    """Encerra a thread da câmera, processa e salva os dados no BD."""
    
    message = "Nenhuma sessão ativa."
    
    # 1. Sinaliza para a thread parar
    stop_tracking_thread()

    # 2. Processamento e Salvamento
    if cam.global_data_collector:
        try:
            # Obtém métricas
            rom_list = cam.global_data_collector.rom_trajectory
            angle_list = cam.global_data_collector.angle_trajectory
            smoothness_score = calculate_smoothness(cam.global_data_collector.hand_center_trajectory)
            end_time = datetime.now() 

            # Cálculo dos Máximos
            max_rom_achieved = np.amax(rom_list) if rom_list else 0.0
            max_angle_achieved = np.amax(angle_list) if angle_list else 0.0
            
            # Obtém a pontuação do jogo, se aplicável
            final_game_score = cam.GAME_SCORE if cam.CURRENT_LOGIC_KEY == 'target_hit_game' else 0

            # Exporta o sumário (CSV)
            data_path = cam.global_data_collector.export_session_data(smoothness_score)
            
            # Salva o registro no banco de dados
            duration = (end_time - cam.global_data_collector.start_time).total_seconds()
            
            new_session = Session(
                patient_id=PATIENT_NAME,
                exercise_name=cam.EXERCISE_NAME,
                start_time=cam.global_data_collector.start_time,
                end_time=end_time,
                duration_seconds=duration,
                smoothness_score=smoothness_score,
                data_file_path=data_path,
                max_rom=max_rom_achieved,
                max_angle=max_angle_achieved,
                game_score=final_game_score
            )
            db.session.add(new_session)
            db.session.commit()

            if cam.CURRENT_LOGIC_KEY == 'target_hit_game':
                 message = f"Sessão de Jogo encerrada! Pontuação Final: {final_game_score}"
            else:
                 message = f"Sessão encerrada. Max ROM: {max_rom_achieved:.2f}, Max Ângulo: {max_angle_achieved:.2f}"

        except Exception as e:
            message = f"Sessão encerrada. Erro ao salvar dados no BD: {e}"
            print(f"Erro ao salvar sessão: {e}")

    # 3. Limpeza final dos globais
    cam.global_data_collector = None
    cam.EXERCISE_NAME = "N/A"
    cam.CURRENT_LOGIC_KEY = "default"
    cam.GAME_SCORE = 0

    return jsonify({"status": "success", "message": message, "redirect": "/metricas"}) 

# --- ROTAS PARA MÉTRICAS E EXPORTAÇÃO ---
@main_bp.route('/metricas')
def metricas():
    sessions = Session.query.order_by(Session.start_time.desc()).all()
    return render_template('metricas.html', sessions=sessions)

@main_bp.route('/export_csv/<int:session_id>')
def export_csv(session_id):
    session = Session.query.get_or_404(session_id)
    
    try:
        return send_file(os.path.abspath(session.data_file_path), 
                         mimetype='text/csv',
                         as_attachment=True,
                         download_name=f"dados_sumario_{session.patient_id}_{session.id}.csv")
    except FileNotFoundError:
        return "Arquivo de dados brutos não encontrado no servidor.", 404
