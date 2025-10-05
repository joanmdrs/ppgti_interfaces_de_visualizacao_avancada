from flask import Blueprint, jsonify, render_template, request, send_file
from datetime import datetime
import json
import numpy as np
import os

# --- MUDANÇAS DE IMPORTAÇÃO NECESSÁRIAS ---
# Os módulos agora são pacotes, e os arquivos devem ser referenciados
# usando o formato 'nome_da_pasta.nome_do_arquivo' (ex: config.config)
from models import db, Session
from config import PATIENT_NAME
from modules.data_collector import DataCollector
from modules.metrics import calculate_smoothness

# O camera_module.py agora está dentro do pacote modules
import camera_module as cam
from camera_module import start_tracking_thread, stop_tracking_thread

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

# ---------------- ROTAS FLASK ----------------

@main_bp.route('/')
def index():
    return render_template('base.html')

@main_bp.route('/exercicios')
def exercicios():
    exercicios_list = carregar_exercicios()
    return render_template('exercicios.html', exercicios=exercicios_list)

@main_bp.route('/start_exercise/<int:exercise_id>')
def start_exercise(exercise_id):
    """Inicia uma nova sessão e a thread da câmera."""
    
    exercicios_list = carregar_exercicios()
    ex = next((e for e in exercicios_list if e['id'] == exercise_id), None)
    if not ex:
        return "Exercício não encontrado", 404
    
    # 1. Atualiza os parâmetros dinâmicos no módulo da câmera
    cam.CURRENT_ROM_MIN = ex.get('rom_min', 100)
    cam.CURRENT_ROM_MAX = ex.get('rom_max', 300)
    cam.CURRENT_METRIC_TYPE = ex.get('metrica', 'ROM (Distância)') 
    
    # 2. Sanitiza o nome e atualiza o estado da câmera
    safe_name = ex['titulo'].replace(' ', '_').replace('/', '_')
    cam.EXERCISE_NAME = safe_name
    
    # 3. Inicializa o DataCollector
    cam.global_data_collector = DataCollector(patient_id=PATIENT_NAME, exercise_name=cam.EXERCISE_NAME)

    # 4. Inicia a thread de rastreio
    start_tracking_thread()
    
    return render_template('control_panel.html', 
                            patient=PATIENT_NAME.replace('_', ' '),
                            exercise=ex['titulo'])


@main_bp.route('/stop_session', methods=['POST'])
def stop_session():
    """Encerra a thread da câmera, processa e salva os dados no BD."""
    
    message = "Nenhuma sessão ativa."
    
    # 1. Sinaliza para a thread parar
    stop_tracking_thread()

    # 2. Processamento e Salvamento
    if cam.global_data_collector:
        try:
            rom_list = cam.global_data_collector.rom_trajectory
            angle_list = cam.global_data_collector.angle_trajectory
            
            # Cálculo dos Máximos
            max_rom_achieved = np.amax(rom_list) if rom_list else 0.0
            max_angle_achieved = np.amax(angle_list) if angle_list else 0.0
            
            smoothness_score = calculate_smoothness(cam.global_data_collector.hand_center_trajectory)
            end_time = datetime.now() 

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
                max_angle=max_angle_achieved
            )
            db.session.add(new_session)
            db.session.commit()

            message = f"Sessão encerrada. Max ROM: {max_rom_achieved:.2f}, Max Ângulo: {max_angle_achieved:.2f}"
        except Exception as e:
            message = f"Sessão encerrada. Erro ao salvar dados no BD: {e}"
            print(f"Erro ao salvar sessão: {e}")

    # 3. Limpeza final dos globais
    cam.global_data_collector = None
    cam.EXERCISE_NAME = "N/A"

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
