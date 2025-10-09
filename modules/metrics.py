# modules/metrics.py
import numpy as np
import math

# Constante de Ponto de Controle (Hand Landmark Index)
# 0: Wrist (Pulso)
# 5: Index finger MCP (Base do indicador)
# 8: Index finger tip (Ponta do indicador)
# 9: Middle finger MCP (Base do dedo médio)
# 12: Middle finger tip (Ponta do dedo médio)
# 17: Pinky MCP (Base do dedo mínimo)

def lm_list_px(hand_landmarks, width, height):
    """Converte coordenadas normalizadas do MediaPipe para coordenadas de pixel."""
    lm_px = []
    for id, lm in enumerate(hand_landmarks.landmark):
        cx, cy = int(lm.x * width), int(lm.y * height)
        lm_px.append((cx, cy))
    return lm_px

def calculate_rom(lm_px):
    """Calcula a distância (ROM) entre a base do indicador (5) e o pulso (0)."""
    if len(lm_px) < 6: return 0.0
    
    # Usando a distância entre o pulso (0) e a base do indicador (5) como ROM de extensão/flexão
    p1 = np.array(lm_px[0])
    p2 = np.array(lm_px[5])
    distance = np.linalg.norm(p1 - p2)
    return distance

def calculate_angle(lm_px, p1_idx, p2_idx, p3_idx):
    """Calcula o ângulo entre três pontos (p2 é o vértice)."""
    if len(lm_px) < max(p1_idx, p2_idx, p3_idx) + 1: return 0.0

    p1 = np.array(lm_px[p1_idx])
    p2 = np.array(lm_px[p2_idx]) # Vértice (Pulso)
    p3 = np.array(lm_px[p3_idx])

    # Vetores
    v1 = p1 - p2
    v2 = p3 - p2
    
    # Cálculo do ângulo em radianos e conversão para graus
    dot_product = np.dot(v1, v2)
    norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)
    
    if norm_product == 0: return 0.0
    
    angle_rad = np.arccos(np.clip(dot_product / norm_product, -1.0, 1.0))
    angle_deg = np.degrees(angle_rad)
    
    # Retorna o ângulo do pulso
    return angle_deg

def calculate_grip_status(lm_px, threshold_ratio=0.15):
    """
    Determina o status da preensão (Fechada/Aberta).
    Usa a distância entre a ponta do indicador (8) e a ponta do polegar (4)
    comparada com a largura da palma (5 a 17).
    """
    if len(lm_px) < 9: return False # Não detectado

    # Distância entre a ponta do indicador (8) e a ponta do polegar (4)
    distance_grip = np.linalg.norm(np.array(lm_px[8]) - np.array(lm_px[4]))
    
    # Largura da palma (5 a 17) para normalização
    palm_width = np.linalg.norm(np.array(lm_px[5]) - np.array(lm_px[17]))
    
    # O aperto é considerado ativo se a distância do aperto for menor que 35% da largura da palma
    if distance_grip < palm_width * 0.35:
        return True # Mão Fechada/Aperto Ativo
    
    return False # Mão Aberta
    
def calculate_smoothness(trajectory):
    """
    Cálculo de suavidade (Placeholder).
    Em um sistema real, calcularia o Jerk (derivada da aceleração)
    para medir a fluidez do movimento.
    """
    if len(trajectory) < 10: return 0.0
    
    # Simula um score de suavidade com base no número de pontos, 
    # garantindo que o valor seja razoável para a exibição.
    base_smoothness = 1.0 + len(trajectory) / 1000.0
    return np.random.uniform(base_smoothness * 0.9, base_smoothness * 1.1)