import cv2
import time
import mediapipe as mp
import threading
from modules.metrics import calculate_rom, calculate_smoothness, calculate_angle, lm_list_px
from config import WINDOW_NAME

# --- VARIÁVEIS GLOBAIS DE ESTADO DA CÂMERA ---
video_camera = None
global_data_collector = None
CAMERA_RUNNING = False 

# Variáveis dinâmicas do exercício
EXERCISE_NAME = "N/A"
CURRENT_ROM_MIN = 100 
CURRENT_ROM_MAX = 300
CURRENT_METRIC_TYPE = "ROM (Distância)" 

# Configurações MediaPipe (Inicializadas via setup_mediapipe)
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = None 

# --- FUNÇÕES DE CONTROLE ---

def setup_mediapipe():
    """Inicializa o objeto hands do MediaPipe globalmente."""
    global hands
    # Max_num_hands=1 (rastreio de uma mão por vez)
    hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)

def start_tracking_thread():
    """Inicia a thread de rastreio se não estiver rodando."""
    global CAMERA_RUNNING
    if not CAMERA_RUNNING:
        threading.Thread(target=tracking_thread_function, daemon=True).start()

def stop_tracking_thread():
    """Sinaliza para a thread de rastreio parar."""
    global CAMERA_RUNNING
    CAMERA_RUNNING = False

# ---------------- FUNÇÃO DE RASTREIO E EXIBIÇÃO NATIVA (CV2.IMSHOW) ----------------
def tracking_thread_function():
    """Captura da câmera, rastreia e exibe em janela nativa CV2."""
    global video_camera, global_data_collector, CAMERA_RUNNING
    global CURRENT_ROM_MIN, CURRENT_ROM_MAX, CURRENT_METRIC_TYPE, EXERCISE_NAME

    print("[INFO] Thread de rastreio nativa iniciada.")
    
    # Inicialização da Câmera
    video_camera = cv2.VideoCapture(0) # Tente cv2.VideoCapture(1) se não funcionar
    time.sleep(1) 

    if not video_camera.isOpened():
        print("ERRO: Não foi possível abrir a câmera.")
        CAMERA_RUNNING = False
        return

    CAMERA_RUNNING = True
    cv2.namedWindow(WINDOW_NAME) 

    while CAMERA_RUNNING:
        success, frame = video_camera.read()
        if not success:
            break
        
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Processamento MediaPipe
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
                
                # --- LÓGICA DE FEEDBACK VISUAL CV2 PARAMETRIZADA (REMOVIDA PARA CONCISÃO) ---
                metric_value = current_rom if CURRENT_METRIC_TYPE == "ROM (Distância)" else wrist_angle
                rom_range = CURRENT_ROM_MAX - CURRENT_ROM_MIN
                progress = min(1.0, max(0.0, (metric_value - CURRENT_ROM_MIN) / rom_range))
                
                # Desenha o Medidor de Progresso (Barra Lateral)
                BAR_HEIGHT = 400; BAR_WIDTH = 30; bar_y_start = 150; bar_x = w - 50
                cv2.rectangle(frame, (bar_x, bar_y_start), (bar_x + BAR_WIDTH, bar_y_start + BAR_HEIGHT), (50, 50, 50), -1)
                fill_height = int(BAR_HEIGHT * progress)
                color = (0, 255, 0) if progress >= 0.95 else (0, 165, 255)
                cv2.rectangle(frame, (bar_x, bar_y_start + BAR_HEIGHT - fill_height), (bar_x + BAR_WIDTH, bar_y_start + BAR_HEIGHT), color, -1)
                cv2.putText(frame, f"{int(progress * 100)}%", (bar_x, bar_y_start - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                # ---------------- FIM LÓGICA DE FEEDBACK ----------------

        # Feedback Numérico na Tela NATIVA
        cv2.putText(frame, f"Exercicio: {EXERCISE_NAME.replace('_', ' ')}", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        if CURRENT_METRIC_TYPE == "ROM (Distância)":
             cv2.putText(frame, f"ROM (Dist.): {current_rom:.2f}", (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
             cv2.putText(frame, f"Angulo: {wrist_angle:.2f} deg", (12, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
        else: 
             cv2.putText(frame, f"Angulo (Graus): {wrist_angle:.2f} deg", (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
             cv2.putText(frame, f"ROM: {current_rom:.2f}", (12, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)

        cv2.imshow(WINDOW_NAME, frame)
        
        if cv2.waitKey(5) & 0xFF == 27:
            CAMERA_RUNNING = False
            break 
            
    print("[INFO] Thread de rastreio nativa encerrada.")
    
    # Limpeza
    if video_camera:
        video_camera.release()
    cv2.destroyAllWindows()
