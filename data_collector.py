from datetime import datetime
import pandas as pd

class DataCollector:
    def __init__(self, patient_id="Paciente_Padrao", exercise_name="Exercício_Geral"):
        self.patient_id = patient_id
        self.exercise_name = exercise_name 
        self.session_start_time = datetime.now()
        self.log = []
        self.hand_center_trajectory = []

    def log_frame_data(self, current_rom, new_angle, hand_lm_px, w, h):
        """
        Armazena os dados de um único frame, incluindo ROM e Ângulo.
        """
        if not hand_lm_px:
            return

        relative_time = (datetime.now() - self.session_start_time).total_seconds()
        
        # Posição do Marco 9 (Centro da Palma)
        hand_center_x, hand_center_y = hand_lm_px[9]
        
        # Armazena a posição para calcular a suavidade
        self.hand_center_trajectory.append((hand_center_x, hand_center_y))

        frame_data = {
            "patient_name": self.patient_id,    
            "exercise": self.exercise_name,     
            "time_s": relative_time,
            "angle_degrees": new_angle,         # CAMPO REQUISITADO
            "rom_normalized": current_rom,      # CAMPO REQUISITADO
            "hand_x": hand_center_x,
            "hand_y": hand_center_y,
            "cam_w": w,
            "cam_h": h,
        }
        self.log.append(frame_data)

    def export_session_data(self, smoothness_score):
        """
        Exporta todos os dados coletados para um arquivo CSV.
        """
        if not self.log:
            print("\n[AVISO] Nenhuma atividade registrada para exportação.")
            return

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sessao_{self.patient_id}_{self.exercise_name}_{timestamp_str}.csv"
        
        # Adiciona a métrica final (Suavidade) como metadado no topo
        metadata_header = f"# Metadado; Suavidade Total (Jerk); {smoothness_score:.4f}\n"
        
        df = pd.DataFrame(self.log)

        try:
            with open(filename, 'w') as f:
                f.write(metadata_header)
                f.write(df.to_csv(index=False, sep=',', line_terminator='\n'))
                    
            print(f"\n[SUCESSO] Dados clínicos e métricas salvos em: {filename}")
        except Exception as e:
            print(f"\n[ERRO] Falha ao salvar o arquivo CSV: {e}")