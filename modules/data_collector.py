# modules/data_collector.py

from datetime import datetime
import json
import os
import csv
import numpy as np

class DataCollector:
    def __init__(self, patient_id, exercise_name):
        self.patient_id = patient_id
        self.exercise_name = exercise_name
        self.start_time = datetime.now()
        
        # Estruturas para coletar os dados brutos de cada frame
        self.frame_data = [] # Para salvar os dados de todos os landmarks e métricas
        
        # NOVAS: Listas específicas para calcular o Max ROM e Max Ângulo
        self.rom_trajectory = [] 
        self.angle_trajectory = []
        
        # Para calcular a suavidade (usando o ponto central da mão)
        self.hand_center_trajectory = [] 

    def log_frame_data(self, rom, angle, lm_px, cam_w, cam_h):
        """Registra os dados de um único frame."""
        timestamp = (datetime.now() - self.start_time).total_seconds()
        
        # 1. Armazena dados para o cálculo de Max e Suavidade
        self.rom_trajectory.append(rom)
        self.angle_trajectory.append(angle)
        
        # O ponto 9 (mão central) é usado para o cálculo da suavidade
        if len(lm_px) > 9:
            self.hand_center_trajectory.append(lm_px[9])
        
        # 2. Prepara os dados brutos para exportação
        data_entry = {
            "timestamp": timestamp,
            "rom": rom,
            "angle": angle,
            "cam_w": cam_w,
            "cam_h": cam_h
        }
        
        # Adiciona as 21 coordenadas (x, y) dos landmarks
        for i, (x, y) in enumerate(lm_px):
            data_entry[f"lm{i}_x"] = x
            data_entry[f"lm{i}_y"] = y
            
        self.frame_data.append(data_entry)

    def export_session_data(self, smoothness_score):
        """Exporta os dados brutos para um arquivo CSV e retorna o caminho."""
        
        # Cria a pasta se não existir
        output_dir = os.path.join('static', 'data', 'sessions', self.patient_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Cria o nome do arquivo
        date_str = self.start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"{self.patient_id}_{self.exercise_name}_{date_str}_raw.csv"
        file_path = os.path.join(output_dir, filename)

        if not self.frame_data:
            print("[ALERTA] Nenhum dado de frame para salvar.")
            return None

        # Define os cabeçalhos do CSV
        fieldnames = list(self.frame_data[0].keys())

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.frame_data)
            
            print(f"[SUCESSO] Dados brutos salvos em: {file_path}")
            return file_path
            
        except Exception as e:
            print(f"[ERRO] Falha ao salvar arquivo CSV: {e}")
            return None