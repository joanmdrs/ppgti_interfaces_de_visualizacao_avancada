import cv2
import mediapipe as mp
import pyautogui
import math
import time
import numpy as np
import sys # NOVO: Para ler argumentos da chamada

# IMPORTAÇÕES MODULARES
from data_collector import DataCollector
from metrics import calculate_rom, calculate_smoothness, calculate_angle 

# ---------------- CONFIG E ARGUMENTOS ----------------
# 1. Leitura de argumentos da interface web (passados via terminal)
if len(sys.argv) < 3:
    print("ERRO: É necessário fornecer o Nome do Paciente e o Exercício.")
    print("Uso: python main.py <Nome_do_Paciente> <Nome_do_Exercicio>")
    sys.exit(1)

PATIENT_NAME = sys.argv[1].replace(' ', '_') 
EXERCISE_NAME = sys.argv[2].replace(' ', '_')

# 2. Configurações do MediaPipe e PyAutoGUI
pyautogui.PAUSE = 0
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.75, min_tracking_confidence=0.75)

cap = cv2.VideoCapture(0)
VIDEO_FEEDBACK = True

# ---- PARAMETROS QUE PODEM SER AJUSTADOS ----
PINCH_NORM_THRESHOLD = 0.05
# ... (outros parâmetros mantidos) ...
SMOOTHING = 0.82

# ---------------- ESTADOS E COLETORES ----------------
mode = "IDLE"
action = "Nenhuma"
prev_mouse_x, prev_mouse_y = pyautogui.position()
# ... (outros estados mantidos) ...

# INICIALIZA O COLETOR DE DADOS com os argumentos da interface
data_collector = DataCollector(patient_id=PATIENT_NAME, exercise_name=EXERCISE_NAME)

# ---------------- FUNÇÕES AUX (lm_list_px, count_extended_fingers, is_pinch_norm, two_hands_centroid) ----------------
# (Mantenha as funções auxiliares aqui, como no código anterior)

def lm_list_px(hand_landmarks, w, h):
    """Converte as coordenadas normalizadas (0 a 1) do MediaPipe para coordenadas em pixels."""
    return [(int(pt.x * w), int(pt.y * h)) for pt in hand_landmarks.landmark]

def count_extended_fingers(lm):
    """Conta quantos dedos estão estendidos."""
    if not lm: return 0
    cnt = 0
    if lm[4][0] < lm[3][0]: cnt += 1
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    for t, p in zip(tips, pips):
        if lm[t][1] < lm[p][1]: cnt += 1
    return cnt

def is_pinch_norm(lm, w, h):
    """Verifica se há o gesto de pinça (pinch) entre o polegar (4) e o indicador (8)"""
    if not lm: return False
    tx_norm, ty_norm = lm[4][0] / w, lm[4][1] / h
    ix_norm, iy_norm = lm[8][0] / w, lm[8][1] / h
    dist_norm = math.hypot(tx_norm - ix_norm, ty_norm - iy_norm)
    return dist_norm < PINCH_NORM_THRESHOLD

def two_hands_centroid(lm1, lm2):
    """Calcula a distância entre o centro da palma (Marco 9) de duas mãos."""
    x1, y1 = lm1[9][0], lm1[9][1]
    x2, y2 = lm2[9][0], lm2[9][1]
    return math.hypot(x1 - x2, y1 - y2)


# ---------------- LOOP PRINCIPAL ----------------
try:
    while True:
        ret, frame = cap.read()
        if not ret: break

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        detected_mode = "IDLE"
        action = "Nenhuma"
        current_rom = 0.0
        wrist_angle = 0.0 # NOVO: Variável para o ângulo

        hands_data = []
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                lm_px = lm_list_px(hand_landmarks, w, h)
                ext_count = count_extended_fingers(lm_px)
                hands_data.append({"lm": lm_px, "ext": ext_count, "raw": hand_landmarks})
            
            # Cálculo das Métricas Clínicas
            current_rom = calculate_rom(hands_data[0]["lm"])
            # Ângulo do Punho (Vértice=0)
            wrist_angle = calculate_angle(hands_data[0]["lm"], 5, 0, 17)
            
            # --- COLETA DE DADOS: Chama o coletor com ROM e Ângulo ---
            data_collector.log_frame_data(detected_mode, hands_data, w, h, current_rom, wrist_angle)

        # --- DETECÇÃO DE MODO (Gestos) ---
        # (Lógica completa de detecção de gestos (ZOOM, WORKSPACE, SCROLL, MOUSE) aqui.
        # Por brevidade, omitida, mas deve ser a mesma do código modular anterior.)
        
        # Lógica resumida de detecção (substitua pela sua lógica completa):
        if len(hands_data) == 1:
            ext_count = hands_data[0]["ext"]
            if ext_count == 2: detected_mode = "SCROLL"
            elif ext_count == 1: detected_mode = "MOUSE"
            else: detected_mode = "IDLE"
        elif len(hands_data) == 2:
            detected_mode = "ZOOM"
        
        # Re-log da informação com o MODO ATUALIZADO (mais preciso)
        if hands_data:
            data_collector.log[-1]["mode"] = detected_mode
            
        # --- AÇÃO POR MODO (MANTIDA) ---
        # (Lógica completa das ações pyAutoGUI para MOUSE, SCROLL, ZOOM, WORKSPACE aqui.)


        # --- SOBREPOSIÇÃO NA TELA (Feedback) ---
        if VIDEO_FEEDBACK:
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            cv2.putText(frame, f"Paciente: {PATIENT_NAME.replace('_', ' ')}", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Exercicio: {EXERCISE_NAME.replace('_', ' ')}", (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"ROM (Abertura): {current_rom:.2f}", (12, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 2)
            cv2.putText(frame, f"Angulo (Punho): {wrist_angle:.2f} deg", (12, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
            
            cv2.imshow("Controle por Gestos - Fisioterapia", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

finally:
    # ---------------- LÓGICA FINAL DE MÉTRICAS E EXPORTAÇÃO ----------------
    smoothness_score = calculate_smoothness(data_collector.hand_center_trajectory)
    data_collector.export_session_data(smoothness_score)

    if cap.isOpened():
        if 'pinch_pressed' in locals() and pinch_pressed: pyautogui.mouseUp()
        cap.release()
        cv2.destroyAllWindows()