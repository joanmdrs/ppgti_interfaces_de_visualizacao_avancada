import math
import numpy as np

def calculate_rom(lm_px):
    """
    Calcula a Amplitude de Movimento (ROM) baseada na distância entre Polegar (4) e Mindinho (20),
    normalizada pelo tamanho da palma (0-9).
    """
    if not lm_px or len(lm_px) < 21:
        return 0.0
    palm_len = math.hypot(lm_px[0][0] - lm_px[9][0], lm_px[0][1] - lm_px[9][1])
    if palm_len == 0:
        return 0.0
    rom_dist = math.hypot(lm_px[4][0] - lm_px[20][0], lm_px[4][1] - lm_px[20][1])
    return rom_dist / palm_len

def calculate_angle(lm_px, p1_idx, p2_idx, p3_idx):
    """
    Calcula o ângulo em graus entre três landmarks (p2 é o vértice).
    """
    if not lm_px or len(lm_px) < 21:
        return 0.0
    p1 = np.array(lm_px[p1_idx])
    p2 = np.array(lm_px[p2_idx])
    p3 = np.array(lm_px[p3_idx])
    vec1 = p1 - p2
    vec2 = p3 - p2
    cosine_angle = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    angle_rad = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return float(np.degrees(angle_rad))

def calculate_smoothness(trajectory_points):
    """
    Calcula a suavidade do movimento usando o Jerk (3ª derivada da posição).
    """
    if len(trajectory_points) < 5:
        return 0.0
    points = np.array(trajectory_points)
    jerk = np.diff(np.diff(np.diff(points, axis=0), axis=0), axis=0)
    jerk_magnitude = np.linalg.norm(jerk, axis=1)
    return float(np.mean(jerk_magnitude)) / 10.0
