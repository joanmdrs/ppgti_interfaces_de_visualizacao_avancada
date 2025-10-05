# modules/metrics.py

import numpy as np
import math

# ---------------- Funções de Conversão e Suporte ----------------

def lm_list_px(hand_landmarks, img_w, img_h):
    """Converte as coordenadas normalizadas do MediaPipe (0 a 1) para coordenadas em pixels."""
    lm_list = []
    for id, lm in enumerate(hand_landmarks.landmark):
        # Multiplica a coordenada normalizada pela largura/altura da imagem
        px_x = int(lm.x * img_w)
        px_y = int(lm.y * img_h)
        lm_list.append((px_x, px_y))
    return lm_list

def calculate_distance(p1, p2):
    """Calcula a distância euclidiana entre dois pontos (x1, y1) e (x2, y2)."""
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

# ---------------- Funções de Métrica Principal ----------------

def calculate_rom(lm_px):
    """
    Calcula uma Amplitude de Movimento (ROM) baseada na distância em pixels.
    
    Usamos a distância entre o pulso (0) e a ponta do dedo médio (12)
    como uma métrica proxy para a ROM vertical/distância.
    """
    if len(lm_px) < 13:
        return 0.0
    
    # Ponto 0: Pulso
    # Ponto 12: Ponta do Dedo Médio
    distance = calculate_distance(lm_px[0], lm_px[12])
    return distance

def calculate_angle(lm_px, p1_idx, p2_idx, p3_idx):
    """
    Calcula o ângulo de um ponto central (p2) em relação a outros dois.
    Usado tipicamente para flexão/extensão do punho.
    
    Exemplo (Flexão/Extensão): p1=5(base do indicador), p2=0(pulso), p3=17(base do mindinho)
    """
    if len(lm_px) < max(p1_idx, p2_idx, p3_idx) + 1:
        return 0.0

    p1 = lm_px[p1_idx]
    p2 = lm_px[p2_idx]
    p3 = lm_px[p3_idx]

    # Calcular o ângulo usando atan2
    angle_radians = math.atan2(p3[1] - p2[1], p3[0] - p2[0]) - \
                    math.atan2(p1[1] - p2[1], p1[0] - p2[0])
    
    angle_degrees = math.degrees(angle_radians)
    
    # Garantir que o ângulo esteja entre 0 e 180 (ângulo interno)
    if angle_degrees < 0:
        angle_degrees += 360
        
    if angle_degrees > 180:
        angle_degrees = 360 - angle_degrees
        
    return abs(angle_degrees)

def calculate_smoothness(trajectory):
    """
    Calcula a suavidade do movimento usando a métrica Junt jerk. 
    
    Mede a variação da aceleração ao longo do tempo. Valores mais baixos = movimento mais suave.
    A trajetória deve ser uma lista de coordenadas (x, y).
    """
    if len(trajectory) < 4:
        return 0.0

    # Converter lista de tuplas para array numpy para cálculos vetoriais
    traj_np = np.array(trajectory)
    
    # 1. Posição (x, y)
    pos = traj_np
    
    # 2. Velocidade (diferença na posição)
    vel = np.diff(pos, axis=0)
    
    # 3. Aceleração (diferença na velocidade)
    acc = np.diff(vel, axis=0)
    
    # 4. Jerk (diferença na aceleração - terceira derivada da posição)
    jerk = np.diff(acc, axis=0)
    
    # 5. Métrica Junt Jerk (Soma dos quadrados da magnitude do jerk)
    # Magnitude (norma) do vetor jerk em cada ponto
    jerk_magnitude_sq = np.sum(jerk**2, axis=1)
    
    # Soma total dos quadrados das magnitudes
    total_jerk_sq = np.sum(jerk_magnitude_sq)
    
    # Normaliza pelo tempo (número de amostras)
    smoothness_score = total_jerk_sq / len(trajectory)

    return smoothness_score