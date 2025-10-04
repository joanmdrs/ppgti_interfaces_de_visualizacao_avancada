# modules/data_collector.py
import csv
from datetime import datetime
import os

class DataCollector:
    def __init__(self, patient_id, exercise_name):
        self.patient_id = patient_id
        self.exercise_name = exercise_name
        self.start_time = datetime.now()
        self.data = []  # Lista que armazenará os frames
        self.hand_center_trajectory = []  # Trajetória dos centros das mãos

        # Cria pasta para salvar os CSVs, se não existir
        self.output_dir = "session_data"
        os.makedirs(self.output_dir, exist_ok=True)

    def log_frame_data(self, rom, wrist_angle, landmarks_px, width, height):
        """Registra dados de cada frame, incluindo timestamp."""
        frame_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        self.data.append({
            "timestamp": frame_time,
            "rom": rom,
            "wrist_angle": wrist_angle,
            "landmarks": landmarks_px,
            "width": width,
            "height": height
        })

        # Calcula centro da mão e salva na trajetória
        cx = sum([p[0] for p in landmarks_px]) / len(landmarks_px)
        cy = sum([p[1] for p in landmarks_px]) / len(landmarks_px)
        self.hand_center_trajectory.append({'cx': cx, 'cy': cy, 'rom': rom, 'angle': wrist_angle, 'timestamp': frame_time})

    def export_session_data(self, smoothness_score=None):
        """Exporta todos os dados coletados para CSV."""
        filename = f"{self.patient_id}_{self.exercise_name}_{self.start_time.strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.output_dir, filename)

        fieldnames = ["timestamp", "rom", "wrist_angle", "width", "height", "landmarks"]
        if smoothness_score is not None:
            fieldnames.append("smoothness_score")

        with open(filepath, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.data:
                row_copy = row.copy()
                if smoothness_score is not None:
                    row_copy["smoothness_score"] = smoothness_score
                row_copy["landmarks"] = str(row_copy["landmarks"])
                writer.writerow(row_copy)

        print(f"[INFO] Dados da sessão salvos em: {filepath}")
        return filepath
