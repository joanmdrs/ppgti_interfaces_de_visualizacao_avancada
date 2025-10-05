# modules/camera_module.py

import cv2
import time
import mediapipe as mp
import threading
import random
import numpy as np
# Importa a nova função de cálculo de preensão (grip)
from modules.metrics import calculate_rom, calculate_angle, lm_list_px, calculate_grip_status
from config.config import WINDOW_NAME

# --- VARIÁVEIS GLOBAIS DE ESTADO DA CÂMERA ---
video_camera = None
global_data_collector = None
CAMERA_RUNNING = False 

# Variáveis dinâmicas de Configuração (Lidas da rota)
EXERCISE_NAME = "N/A"
CURRENT_LOGIC_KEY = "default" 
CURRENT_ROM_MIN = 100 
CURRENT_ROM_MAX = 300
CURRENT_METRIC_TYPE = "ROM (Distância)" 

# Variáveis para Hold Time (Manutenção)
HOLD_TIME_REQUIRED = 0.0
HOLD_TIMER_START = 0.0
HOLD_COMPLETE = False

# Variáveis para a gamificação
TARGET_X = 0
TARGET_Y = 0
TARGET_RADIUS_BASE = 40 
TARGET_SPAWN_TIME = 0
TARGET_DURATION = 2.0
GAME_SCORE = 0
GAME_HIGH_SCORE = 0 # Variável para salvar a maior pontuação da sessão

# Variáveis específicas do Grip Game
GAME_BG_IMAGE = None # Variável global para carregar o fundo apenas uma vez
TARGET_HIT_ZONE = 30 # Distância máxima do cursor para o alvo
IS_GRIPPING = False # Status do aperto da mão

# Configurações MediaPipe
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = None 

# --- FUNÇÕES DE CONTROLE GERAL ---

def setup_mediapipe():
    """Inicializa o objeto hands do MediaPipe globalmente."""
    global hands
    hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)

def start_tracking_thread():
    """Inicia a thread de rastreio se não estiver rodando."""
    global CAMERA_RUNNING, TARGET_SPAWN_TIME, GAME_SCORE, GAME_HIGH_SCORE
    if not CAMERA_RUNNING:
        TARGET_SPAWN_TIME = time.time()
        # Ao iniciar, o GAME_SCORE é resetado, mas o GAME_HIGH_SCORE da sessão anterior é mantido.
        # Se a pontuação máxima deve vir do banco de dados, o frontend precisa injetar esse valor aqui!
        GAME_SCORE = 0 
        threading.Thread(target=tracking_thread_function, daemon=True).start()

def stop_tracking_thread():
    """Sinaliza para a thread de rastreio parar."""
    global CAMERA_RUNNING
    CAMERA_RUNNING = False

# ---------------- FUNÇÕES DE RENDERIZAÇÃO DEDICADAS ----------------

def render_target_hit_game_feedback(frame, w, h, lm_px, hand_center_px, current_rom=None, wrist_angle=None, hand_landmarks_obj=None):
    """
    Lógica dedicada ao 'Jogo: Acerte o Alvo Rápido (Posição)' (ID 3).
    """
    global TARGET_X, TARGET_Y, TARGET_SPAWN_TIME, GAME_SCORE, TARGET_RADIUS_BASE, GAME_HIGH_SCORE
    
    current_time = time.time()
    
    # Desenha Landmarks (para garantir que a mão seja mapeada)
    if hand_landmarks_obj:
        mp_draw.draw_landmarks(frame, hand_landmarks_obj, mp_hands.HAND_CONNECTIONS)
        
    # 1. Verifica Colisão/Pontuação (Apenas posição, sem grip)
    if TARGET_X != 0:
        distance = cv2.norm((TARGET_X, TARGET_Y), hand_center_px)
        
        if distance < TARGET_RADIUS_BASE:
            GAME_SCORE += 10
            
            # --- ATUALIZAÇÃO DO HIGH SCORE (durante a sessão) ---
            if GAME_SCORE > GAME_HIGH_SCORE:
                GAME_HIGH_SCORE = GAME_SCORE
            # --- FIM ATUALIZAÇÃO ---
            
            TARGET_X = 0
            TARGET_Y = 0
            TARGET_SPAWN_TIME = current_time

    # 2. Spawn ou Timeout do Alvo
    if TARGET_X == 0 or (current_time - TARGET_SPAWN_TIME > TARGET_DURATION):
        TARGET_X = random.randint(int(w * 0.2), int(w * 0.8))
        TARGET_Y = random.randint(int(h * 0.2), int(h * 0.8))
        TARGET_SPAWN_TIME = current_time
    
    # 3. Desenho
    if TARGET_X != 0:
        cv2.circle(frame, (TARGET_X, TARGET_Y), TARGET_RADIUS_BASE, (0, 255, 0), 2)
        cv2.circle(frame, (TARGET_X, TARGET_Y), 5, (0, 255, 0), -1)

    cv2.circle(frame, hand_center_px, 15, (255, 100, 255), 3)

    # Display Específico do Jogo
    cv2.putText(frame, f"SCORE: {GAME_SCORE}", (w - 200, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
    cv2.putText(frame, f"MAX SCORE: {GAME_HIGH_SCORE}", (w - 200, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
    
    cv2.putText(frame, f"Tempo Restante: {TARGET_DURATION - (current_time - TARGET_SPAWN_TIME):.1f}s", 
                (w - 200, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 255), 1)

    return frame

def render_grip_score_game_feedback(frame, w, h, lm_px, hand_center_px, current_rom=None, wrist_angle=None, hand_landmarks_obj=None):
    """
    Lógica dedicada ao 'Jogo: Agarrar o Alvo 3D' (ID 4).
    Requer: Posição do cursor + Ação de Fechar a Mão.
    """
    global TARGET_X, TARGET_Y, TARGET_SPAWN_TIME, GAME_SCORE, TARGET_DURATION, GAME_HIGH_SCORE
    global GAME_BG_IMAGE, TARGET_HIT_ZONE, IS_GRIPPING

    current_time = time.time()

    # --- 1. CONFIGURAÇÃO DE IMAGEM DE FUNDO (Carrega apenas uma vez) ---
    if GAME_BG_IMAGE is None:
        try:
            # Usando uma cor sólida cinza escura como fundo 3D.
            GAME_BG_IMAGE = np.zeros((h, w, 3), dtype=np.uint8) + 30 
        except Exception as e:
            print(f"Erro ao carregar imagem de fundo: {e}")
            GAME_BG_IMAGE = frame.copy() 
    
    # Define o frame como a imagem de fundo (simula o cenário), sobrescrevendo o original.
    frame = GAME_BG_IMAGE.copy() 

    # --- DESENHO DE LANDMARKS DA MÃO (AGORA NO NOVO FUNDO) ---
    if hand_landmarks_obj:
        mp_draw.draw_landmarks(frame, hand_landmarks_obj, mp_hands.HAND_CONNECTIONS)

    # --- 2. LÓGICA DE AGARRAR (GRIP) ---
    if lm_px:
        # Verifica se a mão está fechada/apertando
        IS_GRIPPING = calculate_grip_status(lm_px)
    
    grip_color = (0, 0, 255) if IS_GRIPPING else (255, 0, 0)
    grip_text = "APERTANDO!" if IS_GRIPPING else "MÃO ABERTA"
    cv2.putText(frame, f"GRIP: {grip_text}", (12, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, grip_color, 2)


    # --- 3. LÓGICA DO ALVO (Simulação 3D) ---
    if TARGET_X == 0 or (current_time - TARGET_SPAWN_TIME > TARGET_DURATION):
        # Spawna um novo alvo
        TARGET_X = random.randint(int(w * 0.15), int(w * 0.85))
        TARGET_Y = random.randint(int(h * 0.2), int(h * 0.8)) # Y define a 'profundidade'
        TARGET_SPAWN_TIME = current_time
    
    # Escala '3D' do alvo: Quanto mais baixo (maior Y), maior o raio (mais perto)
    scale_factor = 1.0 + (TARGET_Y / h) * 0.8 # Fator de escala de 1.0 a 1.8
    target_radius = int(TARGET_RADIUS_BASE * scale_factor)

    # Verifica se a mão está sobre o alvo
    distance = cv2.norm((TARGET_X, TARGET_Y), hand_center_px)
    is_over_target = distance < target_radius + TARGET_HIT_ZONE
    
    target_base_color = (255, 100, 0) # Azul/Laranja (Alvo distante)

    if is_over_target:
        target_base_color = (0, 255, 255) # Amarelo (Sobre o alvo)
        if IS_GRIPPING:
            # PONTUAÇÃO: Acertou o alvo E agarrou!
            GAME_SCORE += 10
            
            # --- ATUALIZAÇÃO DO HIGH SCORE (durante a sessão) ---
            if GAME_SCORE > GAME_HIGH_SCORE:
                GAME_HIGH_SCORE = GAME_SCORE
            # --- FIM ATUALIZAÇÃO ---
            
            TARGET_X = 0 # Respawna o alvo
            TARGET_Y = 0
            TARGET_SPAWN_TIME = current_time
            target_base_color = (0, 255, 0) # Verde (Pontuado!)


    # Desenho do Alvo (Simulando uma esfera)
    # 1. Círculo principal (cor base)
    cv2.circle(frame, (TARGET_X, TARGET_Y), target_radius, target_base_color, -1)
    # 2. Borda
    cv2.circle(frame, (TARGET_X, TARGET_Y), target_radius, (200, 200, 200), 2)
    # 3. Brilho (para dar a sensação de 3D/esfera)
    cv2.circle(frame, (TARGET_X - int(target_radius * 0.3), TARGET_Y - int(target_radius * 0.3)), 
               int(target_radius * 0.3), (255, 255, 255), -1)

    
    # Desenho do Cursor (Ponto 9)
    cursor_color = (0, 0, 255) if IS_GRIPPING else (255, 100, 255)
    cv2.circle(frame, hand_center_px, 15, cursor_color, 3)

    # Display Específico do Jogo
    cv2.putText(frame, f"SCORE: {GAME_SCORE}", (w - 200, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
    # NOVO DISPLAY: Pontuação Máxima
    cv2.putText(frame, f"MAX SCORE: {GAME_HIGH_SCORE}", (w - 200, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
    
    cv2.putText(frame, f"Tempo Restante: {TARGET_DURATION - (current_time - TARGET_SPAWN_TIME):.1f}s", 
                (w - 200, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 255), 1)

    return frame


def render_flexao_punho_feedback(frame, w, h, lm_px, hand_center_px, current_rom=None, wrist_angle=None, hand_landmarks_obj=None):
    """Lógica dedicada à Flexão de Punho (ROM/Distância)."""
    if hand_landmarks_obj:
        mp_draw.draw_landmarks(frame, hand_landmarks_obj, mp_hands.HAND_CONNECTIONS)
        
    metric_value = current_rom
    return _render_standard_logic(frame, w, h, metric_value, current_rom, wrist_angle)


def render_extensao_cotovelo_feedback(frame, w, h, lm_px, hand_center_px, current_rom, wrist_angle, hand_landmarks_obj=None):
    """Lógica dedicada à Extensão do Cotovelo (Ângulo)."""
    if hand_landmarks_obj:
        mp_draw.draw_landmarks(frame, hand_landmarks_obj, mp_hands.HAND_CONNECTIONS)

    metric_value = wrist_angle
    return _render_standard_logic(frame, w, h, metric_value, current_rom, wrist_angle)


def _render_standard_logic(frame, w, h, metric_value, current_rom, wrist_angle, hand_landmarks_obj=None):
    """Função auxiliar que contém a lógica de Status, Hold Time e Barra Lateral comum."""
    global CURRENT_ROM_MIN, CURRENT_ROM_MAX, CURRENT_METRIC_TYPE
    global HOLD_TIME_REQUIRED, HOLD_TIMER_START, HOLD_COMPLETE

    rom_range = CURRENT_ROM_MAX - CURRENT_ROM_MIN
    
    if rom_range <= 0: progress = 0.0
    else: progress = min(1.0, max(0.0, (metric_value - CURRENT_ROM_MIN) / rom_range))
    
    # --- 1. LÓGICA DE FEEDBACK DE PERFORMANCE (ROM) ---
    ROM_OPTIMAL_THRESHOLD = 0.90
    ROM_LOW_THRESHOLD = 0.10      
    
    performance_text = "Movimento em Andamento"
    performance_color = (0, 165, 255) 

    if progress >= ROM_OPTIMAL_THRESHOLD:
        performance_text = "POSIÇÃO ÓTIMA (Manter!)"
        performance_color = (0, 255, 0)
    elif progress <= ROM_LOW_THRESHOLD:
        performance_text = "REINICIAR/MUITO LONGE"
        performance_color = (0, 0, 255)
    
    cv2.putText(frame, f"STATUS: {performance_text}", 
                (12, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, performance_color, 2)
    
    metric_display = f"ROM (Dist.): {current_rom:.2f}" if CURRENT_METRIC_TYPE == "ROM (Distância)" else f"Angulo (Graus): {wrist_angle:.2f} deg"
    cv2.putText(frame, metric_display, (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
    
    # --- 2. LÓGICA DE HOLD TIME ---
    if HOLD_TIME_REQUIRED > 0:
        current_time = time.time()
        
        if progress >= ROM_OPTIMAL_THRESHOLD and not HOLD_COMPLETE:
            if HOLD_TIMER_START == 0.0: HOLD_TIMER_START = current_time
            
            time_elapsed = current_time - HOLD_TIMER_START
            time_remaining = max(0.0, HOLD_TIME_REQUIRED - time_elapsed)

            if time_elapsed >= HOLD_TIME_REQUIRED:
                HOLD_COMPLETE = True
                hold_text = "MANUTENÇÃO CONCLUÍDA!"
                hold_color = (255, 255, 0)
            else:
                bar_x_hold = 200; bar_y_hold = 165; bar_w_hold = 300; bar_h_hold = 15
                cv2.rectangle(frame, (bar_x_hold, bar_y_hold), (bar_x_hold + bar_w_hold, bar_y_hold + bar_h_hold), (50, 50, 50), -1)
                
                hold_progress = min(1.0, time_elapsed / HOLD_TIME_REQUIRED)
                fill_w_hold = int(bar_w_hold * hold_progress)
                cv2.rectangle(frame, (bar_x_hold, bar_y_hold), (bar_x_hold + fill_w_hold, bar_y_hold + bar_h_hold), (0, 200, 200), -1) 
                              
                hold_text = f"EM MANUTENÇÃO: {time_remaining:.1f}s"
                hold_color = (0, 255, 255)
        elif HOLD_COMPLETE:
            hold_text = "MANUTENÇÃO CONCLUÍDA!"
            hold_color = (255, 255, 0)
        else:
            HOLD_TIMER_START = 0.0 
            hold_text = f"MANUTENÇÃO REQUERIDA: {HOLD_TIME_REQUIRED:.1f}s"
            hold_color = (255, 255, 255)

        cv2.putText(frame, f"HOLD: {hold_text}", 
                    (12, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, hold_color, 2)


    # --- 3. Desenho do Medidor de Progresso (Barra Lateral) ---
    BAR_HEIGHT = 400; BAR_WIDTH = 30; bar_y_start = 150; bar_x = w - 50
    cv2.rectangle(frame, (bar_x, bar_y_start), (bar_x + BAR_WIDTH, bar_y_start + BAR_HEIGHT), (50, 50, 50), -1)
    fill_height = int(BAR_HEIGHT * progress)
    color = (0, 255, 0) if progress >= ROM_OPTIMAL_THRESHOLD else (0, 165, 255) 
    cv2.rectangle(frame, (bar_x, bar_y_start + BAR_HEIGHT - fill_height), (bar_x + BAR_WIDTH, bar_y_start + BAR_HEIGHT), color, -1)
    cv2.putText(frame, f"{int(progress * 100)}%", (bar_x, bar_y_start - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
    return frame

# --- DICIONÁRIO DE DESPACHO (Dispatch Table) ---
# Mapeia a logic_key do JSON para a função correta
LOGIC_DISPATCHER = {
    "flexao_punho": render_flexao_punho_feedback,
    "extensao_cotovelo": render_extensao_cotovelo_feedback,
    "target_hit_game": render_target_hit_game_feedback,
    "grip_score_game": render_grip_score_game_feedback, # NOVO JOGO!
}


# ---------------- FUNÇÃO DE RASTREIO PRINCIPAL (Dispatch) ----------------

def tracking_thread_function():
    """Captura da câmera, rastreia, registra dados e despacha a renderização.
       CHAMADA PADRONIZADA: agora sempre 8 argumentos.
    """
    global video_camera, global_data_collector, CAMERA_RUNNING
    global EXERCISE_NAME, CURRENT_LOGIC_KEY, GAME_HIGH_SCORE

    video_camera = cv2.VideoCapture(0)
    time.sleep(1) 

    if not video_camera.isOpened():
        print("ERRO: Não foi possível abrir a câmera.")
        CAMERA_RUNNING = False
        return

    CAMERA_RUNNING = True
    cv2.namedWindow(WINDOW_NAME) 
    
    render_func = LOGIC_DISPATCHER.get(CURRENT_LOGIC_KEY)
    if not render_func:
        print(f"[ERRO FATAL] Logic Key '{CURRENT_LOGIC_KEY}' não encontrada no dispatcher.")
        stop_tracking_thread()
        return

    while CAMERA_RUNNING:
        success, frame = video_camera.read()
        if not success: break
        
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb) 
        
        lm_px = []
        hand_center_px = (0, 0) 
        current_rom = 0.0
        wrist_angle = 0.0

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                lm_px = lm_list_px(hand_landmarks, w, h)
                current_rom = calculate_rom(lm_px)
                wrist_angle = calculate_angle(lm_px, 5, 0, 17) 
                
                # NOTE: O desenho dos landmarks (mp_draw.draw_landmarks) foi movido para dentro
                # das funções de renderização dedicadas para garantir a visibilidade,
                # especialmente quando um fundo de jogo personalizado é aplicado.
                
                if len(lm_px) > 9:
                    hand_center_px = lm_px[9]

                # Loga o dado
                if global_data_collector:
                    global_data_collector.log_frame_data(current_rom, wrist_angle, lm_px, w, h)
                
                # --- CHAMADA PADRONIZADA À FUNÇÃO DEDICADA (AGORA COM 8 ARGUMENTOS) ---
                try:
                    # O último argumento é o objeto hand_landmarks do MediaPipe
                    frame = render_func(frame, w, h, lm_px, hand_center_px, current_rom, wrist_angle, hand_landmarks)
                except Exception as e:
                    print(f"[ERRO DE RENDERIZAÇÃO]: {e}")
                    
        
        # Feedback Comum
        cv2.putText(frame, f"Exercicio: {EXERCISE_NAME.replace('_', ' ')}", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow(WINDOW_NAME, frame)
        
        if cv2.waitKey(5) & 0xFF == 27:
            CAMERA_RUNNING = False
            break 
            
    print("[INFO] Thread de rastreio nativa encerrada.")
    
    # --- NOVO: LÓGICA DE EXPOSIÇÃO DE PONTUAÇÃO MÁXIMA PARA SALVAMENTO ---
    if global_data_collector and (CURRENT_LOGIC_KEY == "target_hit_game" or CURRENT_LOGIC_KEY == "grip_score_game"):
        # Se um dos jogos estava ativo, registra a pontuação máxima final no coletor.
        # ASSUME que o frontend/App está lendo este coletor no final da sessão para salvar no Firestore.
        if GAME_HIGH_SCORE > 0:
            print(f"[DATA] Final Score: Expondo High Score de {GAME_HIGH_SCORE} para {CURRENT_LOGIC_KEY} no coletor.")
            # Chamamos um método fictício para sinalizar que este é o dado final do jogo.
            # No ambiente real, o coletor de dados leria o `GAME_HIGH_SCORE` final.
            # Assumimos que o coletor de dados tem uma forma de salvar essa informação.
            try:
                global_data_collector.log_game_score(CURRENT_LOGIC_KEY, GAME_HIGH_SCORE)
            except AttributeError:
                # Fallback se o método não existir
                pass
            
    # --- FIM LÓGICA DE EXPOSIÇÃO ---
    
    if video_camera:
        video_camera.release()
    cv2.destroyAllWindows()
