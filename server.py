import cv2
import time
import mediapipe as mp
from flask import Flask, jsonify, render_template, Response, stream_with_context
import json

from modules.data_collector import DataCollector
from modules.metrics import calculate_rom, calculate_smoothness, calculate_angle

# --- CONFIGURAÇÃO GLOBAL ---
app = Flask(__name__)

video_camera = None
global_data_collector = None
PATIENT_NAME = "Paciente_Padrao"
EXERCISE_NAME = "N/A"

# Configuração do MediaPipe
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)

# ---------------- FUNÇÃO AUXILIAR ----------------
def lm_list_px(hand_landmarks, w, h):
    """Converte coordenadas normalizadas para pixels."""
    return [(int(pt.x * w), int(pt.y * h)) for pt in hand_landmarks.landmark]

# ---------------- FUNÇÃO DE GERAÇÃO DE FRAMES ----------------
def generate_frames():
    global video_camera, global_data_collector, PATIENT_NAME, EXERCISE_NAME

    if video_camera is None:
        video_camera = cv2.VideoCapture(0)
        time.sleep(1)

    if not video_camera.isOpened():
        print("ERRO: Não foi possível abrir a câmera.")
        return

    while True:
        success, frame = video_camera.read()
        if not success:
            break
        
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        current_rom = 0.0
        wrist_angle = 0.0

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                lm_px = lm_list_px(hand_landmarks, w, h)
                current_rom = calculate_rom(lm_px)
                wrist_angle = calculate_angle(lm_px, 5, 0, 17)

                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                if global_data_collector:
                    global_data_collector.log_frame_data(current_rom, wrist_angle, lm_px, w, h)

        # Feedback visual
        cv2.putText(frame, f"Paciente: {PATIENT_NAME.replace('_', ' ')}", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Exercicio: {EXERCISE_NAME.replace('_', ' ')}", (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"ROM: {current_rom:.2f}", (12, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 2)
        cv2.putText(frame, f"Angulo: {wrist_angle:.2f} deg", (12, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# ---------------- FUNÇÃO PARA CARREGAR EXERCICIOS ----------------
def carregar_exercicios():
    with open('static/data/exercicios.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# ---------------- ROTAS FLASK ----------------
@app.route('/')
def index():
    return render_template('base.html')

@app.route('/exercicios')
def exercicios():
    exercicios = carregar_exercicios()
    return render_template('exercicios.html', exercicios=exercicios)

@app.route('/start_exercise/<int:exercise_id>')
def start_exercise(exercise_id):
    global EXERCISE_NAME, global_data_collector

    exercicios = carregar_exercicios()
    ex = next((e for e in exercicios if e['id'] == exercise_id), None)
    if not ex:
        return "Exercício não encontrado", 404

    EXERCISE_NAME = ex['titulo'].replace(' ', '_')

    # Inicializa o coletor de dados
    global_data_collector = DataCollector(patient_id=PATIENT_NAME, exercise_name=EXERCISE_NAME)

    return render_template('streaming.html', 
                           patient=PATIENT_NAME.replace('_', ' '),
                           exercise=EXERCISE_NAME.replace('_', ' '))

@app.route('/video_feed')
def video_feed():
    return Response(stream_with_context(generate_frames()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_session', methods=['POST'])
def stop_session():
    global video_camera, global_data_collector, PATIENT_NAME, EXERCISE_NAME
    message = "Nenhuma sessão ativa."

    if global_data_collector:
        smoothness_score = calculate_smoothness(global_data_collector.hand_center_trajectory)
        global_data_collector.export_session_data(smoothness_score)
        message = f"Sessão encerrada e dados salvos. Suavidade: {smoothness_score:.4f}"

    if video_camera:
        video_camera.release()
        video_camera = None

    global_data_collector = None
    EXERCISE_NAME = "N/A"

    return jsonify({"status": "success", "message": message, "redirect": "/"})

# ---------------- EXECUÇÃO ----------------
if __name__ == '__main__':
    app.run(debug=True, port=5000)
