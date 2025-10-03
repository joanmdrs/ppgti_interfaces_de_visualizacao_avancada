import cv2
import time
import subprocess
import threading
import os
import mediapipe as mp
from flask import Flask, request, jsonify, render_template, Response, stream_with_context

# IMPORTAÇÕES MODULARES (Garantir que os arquivos estejam na mesma pasta)
from data_collector import DataCollector
from metrics import calculate_rom, calculate_smoothness, calculate_angle, lm_list_px

# --- CONFIGURAÇÃO GLOBAL ---
app = Flask(__name__)

# Variáveis globais para streaming e coleta de dados
video_camera = None
global_data_collector = None
PATIENT_NAME = "N/A"
EXERCISE_NAME = "N/A"

# Configuração do MediaPipe
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)


# ---------------- FUNÇÃO DE GERAÇÃO DE FRAMES (Core do Processamento) ----------------
def generate_frames():
    """Gera frames de vídeo com os dados do MediaPipe para o navegador (MJPEG Stream)."""
    global video_camera, global_data_collector, PATIENT_NAME, EXERCISE_NAME
    
    # Inicializa a câmera se não estiver ativa
    if video_camera is None:
        # Tenta a primeira câmera disponível
        video_camera = cv2.VideoCapture(0)
        time.sleep(1) # Aguarda para a câmera iniciar

    if not video_camera.isOpened():
        print("ERRO: Não foi possível abrir a câmera.")
        return

    while True:
        success, frame = video_camera.read()
        if not success:
            break
        
        # Pré-processamento
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)
        
        current_rom = 0.0
        wrist_angle = 0.0

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                lm_px = lm_list_px(hand_landmarks, w, h)
                
                # CÁLCULO DAS MÉTRICAS
                current_rom = calculate_rom(lm_px)
                # Ângulo do Punho (Vértice=0: Pulso)
                wrist_angle = calculate_angle(lm_px, 5, 0, 17) 

                # DESENHA LANDMARKS NO FRAME
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # LOG DE DADOS (Se o coletor foi inicializado)
                if global_data_collector:
                    global_data_collector.log_frame_data(current_rom, wrist_angle, lm_px, w, h)

            
        # FEEDBACK VISUAL
        cv2.putText(frame, f"Paciente: {PATIENT_NAME.replace('_', ' ')}", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Exercicio: {EXERCISE_NAME.replace('_', ' ')}", (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"ROM: {current_rom:.2f}", (12, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 2)
        cv2.putText(frame, f"Angulo: {wrist_angle:.2f} deg", (12, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)


        # Codifica o frame para o formato JPEG (necessário para streaming web)
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        # Envia o frame formatado (MJPEG)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# ---------------- ROTAS FLASK ----------------

@app.route('/')
def index():
    """Serve a página HTML do menu de exercícios."""
    return render_template('web_interface.html')

@app.route('/start_session', methods=['POST'])
def start_session():
    """Inicia a sessão, inicializa o coletor e retorna a rota para o streaming."""
    global PATIENT_NAME, EXERCISE_NAME, global_data_collector
    
    data = request.json
    # Limpa espaços e caracteres especiais para uso seguro em URLs/arquivos
    patient_name = data.get('patient_name', 'Paciente_Desconhecido').replace(' ', '_')
    exercise_name = data.get('exercise_name', 'Exercicio_Geral').replace(' ', '_')

    # 1. ATUALIZA ESTADOS GLOBAIS
    PATIENT_NAME = patient_name
    EXERCISE_NAME = exercise_name
    
    # 2. INICIALIZA O COLETOR DE DADOS
    global_data_collector = DataCollector(patient_id=PATIENT_NAME, exercise_name=EXERCISE_NAME)

    return jsonify({
        "status": "success", 
        "message": "Sessão iniciada! Redirecionando...", 
        "redirect": "/streaming"
    })

@app.route('/streaming')
def streaming_page():
    """Página que contém o elemento <img> para o stream de vídeo."""
    # Renderiza a página de streaming, passando os nomes para exibição
    return render_template('streaming.html', 
                           patient=PATIENT_NAME.replace('_', ' '), 
                           exercise=EXERCISE_NAME.replace('_', ' '))

@app.route('/video_feed')
def video_feed():
    """Rota que entrega os frames do OpenCV como um stream MJPEG."""
    # O Response com 'multipart/x-mixed-replace' é o que permite o streaming contínuo
    return Response(stream_with_context(generate_frames()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_session', methods=['POST'])
def stop_session():
    """Para a câmera, salva os dados e limpa os estados globais."""
    global video_camera, global_data_collector, PATIENT_NAME, EXERCISE_NAME
    
    message = "Nenhuma sessão ativa."
    
    if global_data_collector:
        # 1. Calcula a métrica final e exporta
        smoothness_score = calculate_smoothness(global_data_collector.hand_center_trajectory)
        global_data_collector.export_session_data(smoothness_score)
        message = f"Sessão encerrada e dados salvos. Suavidade: {smoothness_score:.4f}"
        
    # 2. Desliga a câmera e limpa variáveis
    if video_camera:
        video_camera.release()
        video_camera = None

    global_data_collector = None
    PATIENT_NAME = "N/A"
    EXERCISE_NAME = "N/A"
    
    return jsonify({"status": "success", "message": message, "redirect": "/"})


if __name__ == '__main__':
    # Garante que o MediaPipe (hands) esteja configurado antes do loop do Flask
    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils
    
    app.run(debug=True, port=5000)