import cv2
import mediapipe as mp
import pyautogui
import math
import time
import numpy as np

# ---------------- CONFIG ----------------
pyautogui.PAUSE = 0
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
# -- ALTERADO -- Aumentei a confiança para evitar detecções falsas que poderiam atrapalhar
hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.75, min_tracking_confidence=0.75)

cap = cv2.VideoCapture(0)
VIDEO_FEEDBACK = True

# ---- PARAMETROS QUE PODEM SER AJUSTADOS ----
PINCH_NORM_THRESHOLD = 0.05
SCROLL_SENSITIVITY = 4
ZOOM_SENSITIVITY = 15
ZOOM_COOLDOWN = 0.06
MAP_MARGIN = 100
SMOOTHING = 0.82
# -- NOVOS PARÂMETROS PARA O WORKSPACE --
WORKSPACE_NAV_SENSITIVITY = 50  # Distância em pixels que a mão precisa se mover para navegar
WORKSPACE_NAV_COOLDOWN = 0.4    # Tempo em segundos para esperar antes da próxima navegação

# ---------------- ESTADOS ----------------
mode = "IDLE"
action = "Nenhuma"
prev_mouse_x, prev_mouse_y = pyautogui.position()
prev_zoom_dist = None
last_zoom_time = 0
prev_scroll_y = None
pinch_pressed = False
# -- NOVOS ESTADOS PARA O WORKSPACE --
workspace_mode_active = False
prev_workspace_hand_x = None
last_workspace_nav_time = 0


# ---------------- FUNÇÕES AUX ----------------
def lm_list_px(hand_landmarks, w, h):
    return [(int(pt.x * w), int(pt.y * h)) for pt in hand_landmarks.landmark]

# -- ALTERADO -- Simplificada para usar coordenadas em pixels diretamente
def count_extended_fingers(lm):
    if not lm: return 0
    cnt = 0
    # Polegar (lógica especial baseada na posição x)
    if lm[4][0] < lm[3][0]:
        cnt += 1
    # Outros 4 dedos (lógica baseada na posição y)
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    for t, p in zip(tips, pips):
        if lm[t][1] < lm[p][1]:
            cnt += 1
    return cnt

def is_pinch_norm(lm, w, h):
    # Recalcula a distância normalizada para ser independente da resolução
    if not lm: return False
    tx_norm, ty_norm = lm[4][0] / w, lm[4][1] / h
    ix_norm, iy_norm = lm[8][0] / w, lm[8][1] / h
    dist_norm = math.hypot(tx_norm - ix_norm, ty_norm - iy_norm)
    return dist_norm < PINCH_NORM_THRESHOLD

def two_hands_centroid(lm1, lm2):
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

        hands_data = []
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                lm_px = lm_list_px(hand_landmarks, w, h)
                ext_count = count_extended_fingers(lm_px)
                hands_data.append({"lm": lm_px, "ext": ext_count, "raw": hand_landmarks})

        # --- DETECÇÃO DE MODO ---
        if len(hands_data) == 2:
            hand1_ext = hands_data[0]["ext"]
            hand2_ext = hands_data[1]["ext"]
            hand1_is_open = hand1_ext >= 4
            hand2_is_open = hand2_ext >= 4
            hand1_is_closed = hand1_ext <= 1
            hand2_is_closed = hand2_ext <= 1
            
            # -- LÓGICA WORKSPACE ALTERADA --
            # Se já estamos no modo workspace e ambas as mãos se fecham, é uma seleção
            if workspace_mode_active and hand1_is_closed and hand2_is_closed:
                detected_mode = "WORKSPACE_SELECT"
            # Uma mão aberta e uma fechada ativa ou continua o modo de navegação
            elif (hand1_is_open and hand2_is_closed) or (hand2_is_open and hand1_is_closed):
                detected_mode = "WORKSPACE"
            elif hand1_is_open and hand2_is_open:
                detected_mode = "ZOOM"
            else:
                detected_mode = "IDLE"
                
        elif len(hands_data) == 1:
            ext_count = hands_data[0]["ext"]
            if ext_count == 2: # Dedos indicador e médio para cima
                 detected_mode = "SCROLL"
            elif ext_count == 1: # Apenas dedo indicador para cima
                 detected_mode = "MOUSE"
            else:
                 detected_mode = "IDLE"
        else:
            detected_mode = "IDLE"

        # --- Bloco de Limpeza de Estado ---
        # Se sairmos do modo workspace, fecha a Visão de Tarefas e reseta os estados
        if detected_mode not in ["WORKSPACE", "WORKSPACE_SELECT"] and workspace_mode_active:
            pyautogui.press('escape')
            workspace_mode_active = False
            prev_workspace_hand_x = None # Reseta a posição da mão
            action = "Saindo do Workspace"

        # --- AÇÃO POR MODO ---
        if detected_mode == "ZOOM":
            lm1, lm2 = hands_data[0]["lm"], hands_data[1]["lm"]
            dist_px = two_hands_centroid(lm1, lm2)
            now = time.time()
            if prev_zoom_dist is None: prev_zoom_dist = dist_px
            else:
                diff = dist_px - prev_zoom_dist
                if abs(diff) > ZOOM_SENSITIVITY and (now - last_zoom_time) > ZOOM_COOLDOWN:
                    scroll_steps = int(abs(diff) / ZOOM_SENSITIVITY)
                    scroll_value = scroll_steps * 20
                    pyautogui.keyDown('ctrl'); pyautogui.scroll(scroll_value if diff > 0 else -scroll_value); pyautogui.keyUp('ctrl')
                    action = f"Zoom {'IN' if diff > 0 else 'OUT'}"
                    last_zoom_time = now
                    prev_zoom_dist = dist_px

        # -- NOVA LÓGICA COMPLETA PARA WORKSPACE --
        elif detected_mode == "WORKSPACE":
            if not workspace_mode_active:
                pyautogui.hotkey('win', 'tab')
                workspace_mode_active = True
                action = "Workspace: Ativado"
                time.sleep(0.2) # Pequena pausa para a animação do OS
            else:
                # Identifica qual mão está aberta para controlar a navegação
                open_hand_lm = None
                if hands_data[0]["ext"] >= 4: open_hand_lm = hands_data[0]["lm"]
                elif hands_data[1]["ext"] >= 4: open_hand_lm = hands_data[1]["lm"]

                if open_hand_lm:
                    # Usamos o centro da palma (marco 9) para mais estabilidade
                    current_x = open_hand_lm[9][0]
                    now = time.time()

                    if prev_workspace_hand_x is None:
                        prev_workspace_hand_x = current_x # Define a posição inicial de referência
                        action = "Workspace: Mova a mão"
                    else:
                        dx = current_x - prev_workspace_hand_x
                        # Verifica se houve movimento suficiente e se o cooldown passou
                        if (now - last_workspace_nav_time) > WORKSPACE_NAV_COOLDOWN:
                            if dx > WORKSPACE_NAV_SENSITIVITY:
                                pyautogui.press('right')
                                action = "Workspace: Direita ->"
                                prev_workspace_hand_x = current_x # Reseta a referência
                                last_workspace_nav_time = now
                            elif dx < -WORKSPACE_NAV_SENSITIVITY:
                                pyautogui.press('left')
                                action = "Workspace: <- Esquerda"
                                prev_workspace_hand_x = current_x # Reseta a referência
                                last_workspace_nav_time = now
                            else:
                                action = "Workspace: Navegando"
        
        # -- NOVA LÓGICA PARA SELECIONAR NO WORKSPACE --
        elif detected_mode == "WORKSPACE_SELECT":
            if workspace_mode_active:
                pyautogui.press('enter')
                action = "Workspace: Selecionado!"
                workspace_mode_active = False # Desativa o modo
                prev_workspace_hand_x = None # Reseta o estado
                time.sleep(0.5) # Pausa para evitar ações indesejadas

        elif detected_mode == "SCROLL":
            lm = hands_data[0]["lm"]
            idx_y = lm[8][1]
            if prev_scroll_y is None: prev_scroll_y = idx_y
            else:
                dy = prev_scroll_y - idx_y
                scroll_amount = int(dy / SCROLL_SENSITIVITY)
                if abs(scroll_amount) >= 1:
                    pyautogui.scroll(scroll_amount * 15)
                    action = f"Scroll {scroll_amount}"
                    prev_scroll_y = idx_y

        elif detected_mode == "MOUSE":
            lm = hands_data[0]["lm"]
            x_px, y_px = lm[8][0], lm[8][1]
            tx = np.interp(x_px, [MAP_MARGIN, w - MAP_MARGIN], [0, pyautogui.size().width])
            ty = np.interp(y_px, [MAP_MARGIN, h - MAP_MARGIN], [0, pyautogui.size().height])
            mx = prev_mouse_x * SMOOTHING + tx * (1 - SMOOTHING)
            my = prev_mouse_y * SMOOTHING + ty * (1 - SMOOTHING)
            pyautogui.moveTo(int(mx), int(my))
            prev_mouse_x, prev_mouse_y = mx, my
            action = "Movendo"
            
            # Lógica de clique/arrastar com pinch
            if is_pinch_norm(lm, w, h):
                if not pinch_pressed:
                    pyautogui.mouseDown(); pinch_pressed = True
                    action = "Arrastando"
            else:
                if pinch_pressed:
                    pyautogui.mouseUp(); pinch_pressed = False

        else: # IDLE
            if pinch_pressed:
                pyautogui.mouseUp(); pinch_pressed = False
            # Reseta variáveis de scroll e zoom para recalibrar ao reentrar nos modos
            prev_scroll_y = None
            prev_zoom_dist = None
            
        # --- SOBREPOSIÇÃO NA TELA ---
        if VIDEO_FEEDBACK:
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            cv2.putText(frame, f"Modo: {detected_mode}", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 220, 200), 2)
            cv2.putText(frame, f"Acao: {action}", (12, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            cv2.imshow("Controle por Gestos", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

finally:
    if pinch_pressed: pyautogui.mouseUp()
    cap.release()
    cv2.destroyAllWindows()