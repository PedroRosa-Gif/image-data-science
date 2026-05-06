import sys
import numpy as np
import subprocess
import os

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout,
    QFileDialog, QLabel, QSlider, QComboBox, QHBoxLayout,
    QFrame, QGroupBox, QSpinBox
)
from PyQt6.QtGui import QImage, QPixmap, QColor, QPalette, QFont
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QSizePolicy

# =========================
# CONFIG
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIFT_BIN = os.path.abspath(os.path.join(BASE_DIR, "code/DIFT"))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# =========================
# ESTILIZAÇÃO MODERNA (QSS)
# =========================
MODERN_STYLE = """
QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: 'Segoe UI', sans-serif;
}

QGroupBox {
    border: 1px solid #333333;
    border-radius: 8px;
    margin-top: 15px;
    font-weight: bold;
    padding-top: 10px;
}

QPushButton {
    background-color: #3d3d3d;
    border: none;
    border-radius: 4px;
    padding: 8px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #505050;
}

QPushButton#run_btn {
    background-color: #2e7d32;
    font-weight: bold;
}

QPushButton#run_btn:hover {
    background-color: #388e3c;
}

QSlider::handle:horizontal {
    background: #0078d4;
    width: 14px;
    border-radius: 7px;
}

QLabel#status_bar {
    background-color: #2d2d2d;
    padding: 5px;
    border-top: 1px solid #333333;
}
"""


# ... (Funções read_scn e write_scn permanecem as mesmas)
def read_scn(path):
    with open(path, "rb") as f:
        line = f.readline().decode().strip()
        if line != "SCN": return None
        x, y, z = map(int, f.readline().decode().split())
        f.readline()
        bits = int(f.readline().decode())
        dtype = {8: np.uint8, 16: np.uint16, 32: np.int32}[bits]
        data = np.fromfile(f, dtype=dtype)
        return data.reshape((z, y, x))

def write_scn(path, volume):
    z, y, x = volume.shape
    with open(path, "wb") as f:
        f.write(b"SCN\n")
        f.write(f"{x} {y} {z}\n".encode())
        f.write(b"1.0 1.0 1.0\n")
        f.write(b"16\n")
        volume.astype(np.uint16).tofile(f)

# =========================
# IMAGE VIEW MELHORADO
# =========================
class ImageView(QLabel):
    def __init__(self, title, parent_app=None):
        super().__init__()
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("border: 1px solid #333; background: black; border-radius: 4px;")
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        
        self.title_label = QLabel(title, self)
        self.title_label.setStyleSheet("background: rgba(0,0,0,150); color: white; padding: 2px;")
        
        self.parent_app = parent_app
        self.image = None
        self.overlay = None
        self.drawing = False
        

    def set_image(self, img):
        self.image = img.copy()
        self.update_view()

    def set_overlay(self, overlay):
        self.overlay = overlay
        self.update_view()

    def update_view(self):
        if self.image is None:
            return

        img = self.image.copy()

        if self.overlay is not None:
            img[self.overlay == 1] = [255, 0, 0]
            img[self.overlay == 2] = [0, 0, 255]

        h, w, _ = img.shape
        qimg = QImage(img.data, w, h, 3*w, QImage.Format.Format_RGB888).copy()
        
        pixmap = QPixmap.fromImage(qimg)
        
        scaled_pixmap = pixmap.scaled(
            self.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.setPixmap(scaled_pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.draw(event.position())

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.draw(event.position())

    def mouseReleaseEvent(self, event):
        self.drawing = False

    def draw(self, pos):
        if self.overlay is None or self.parent_app.state == "RUNNING": return
        
        # Mapeamento de coordenadas considerando o aspect ratio
        pw = self.pixmap().width()
        ph = self.pixmap().height()
        offset_x = (self.width() - pw) / 2
        offset_y = (self.height() - ph) / 2
        
        rx = (pos.x() - offset_x) / pw
        ry = (pos.y() - offset_y) / ph
        
        if 0 <= rx <= 1 and 0 <= ry <= 1:
            x = int(rx * self.overlay.shape[1])
            y = int(ry * self.overlay.shape[0])
            
            brush = self.parent_app.brush_size
            label = self.parent_app.current_label
            
            # Desenho circular nas seeds
            yy, xx = np.ogrid[-brush:brush, -brush:brush]
            mask = xx**2 + yy**2 <= brush**2
            
            y_start, y_end = max(0, y-brush), min(self.overlay.shape[0], y+brush)
            x_start, x_end = max(0, x-brush), min(self.overlay.shape[1], x+brush)
            
            # Ajuste da máscara para bordas
            m_y_start = brush - (y - y_start)
            m_y_end = brush + (y_end - y)
            m_x_start = brush - (x - x_start)
            m_x_end = brush + (x_end - x)
            
            self.overlay[y_start:y_end, x_start:x_end][mask[m_y_start:m_y_end, m_x_start:m_x_end]] = label
            self.update_view()
            self.parent_app.sync_seeds_to_volume()

# =========================
# APP PRINCIPAL
# =========================
class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DIFT Segmentation Pro")
        self.resize(1280, 800)
        self.setStyleSheet(MODERN_STYLE)
        
        self.state = "IDLE"
        self.brush_size = 5
        self.current_label = 1
        
        self.init_ui()

    def set_status(self, text):
        """Atualiza o texto da barra de status e força a interface a processar o evento."""
        self.status_bar.setText(f"Status: {text}")
        # Isso evita que a interface pareça 'travada' ao mudar o texto
        QApplication.processEvents()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # PAINEL LATERAL
        sidebar = QVBoxLayout()
        sidebar.setSpacing(10)

        # Grupo: Arquivos
        file_group = QGroupBox("PROJETO")
        file_vbox = QVBoxLayout()
        self.btn_load_img = QPushButton("📂 Abrir Volume")
        self.btn_load_seeds = QPushButton("🎯 Importar Seeds")
        file_vbox.addWidget(self.btn_load_img)
        file_vbox.addWidget(self.btn_load_seeds)
        file_group.setLayout(file_vbox)

        # Grupo: Ferramentas
        tools_group = QGroupBox("FERRAMENTAS DE DESENHO")
        tools_vbox = QVBoxLayout()
        
        self.combo_label = QComboBox()
        self.combo_label.addItems(["Objeto (Vermelho)", "Fundo (Azul)"])
        self.combo_label.setStyleSheet("padding: 5px;")
        
        tools_vbox.addWidget(QLabel("Label Ativo:"))
        tools_vbox.addWidget(self.combo_label)
        
        tools_vbox.addWidget(QLabel("Tamanho do Pincel:"))
        self.spin_brush = QSpinBox()
        self.spin_brush.setRange(1, 50)
        self.spin_brush.setValue(5)
        tools_vbox.addWidget(self.spin_brush)
        
        tools_group.setLayout(tools_vbox)

        # Grupo: Navegação
        nav_group = QGroupBox("NAVEGAÇÃO 3D")
        nav_vbox = QVBoxLayout()
        
        self.sld_z = QSlider(Qt.Orientation.Horizontal)
        self.sld_y = QSlider(Qt.Orientation.Horizontal)
        self.sld_x = QSlider(Qt.Orientation.Horizontal)
        
        nav_vbox.addWidget(QLabel("Z (Axial)"))
        nav_vbox.addWidget(self.sld_z)
        nav_vbox.addWidget(QLabel("Y (Coronal)"))
        nav_vbox.addWidget(self.sld_y)
        nav_vbox.addWidget(QLabel("X (Sagital)"))
        nav_vbox.addWidget(self.sld_x)
        nav_group.setLayout(nav_vbox)

        self.btn_run = QPushButton("🚀 EXECUTAR DIFT")
        self.btn_run.setObjectName("run_btn")
        self.btn_run.setMinimumHeight(50)

        sidebar.addWidget(file_group)
        sidebar.addWidget(tools_group)
        sidebar.addWidget(nav_group)
        sidebar.addStretch()
        sidebar.addWidget(self.btn_run)

        # PAINEL DE VISUALIZAÇÃO
        view_layout = QVBoxLayout()
        self.view_axial = ImageView("AXIAL", self)
        self.view_coronal = ImageView("CORONAL", self)
        self.view_sagittal = ImageView("SAGITAL", self)
        
        h_views = QHBoxLayout()
        h_views.addWidget(self.view_axial)
        h_views.addWidget(self.view_coronal)
        h_views.addWidget(self.view_sagittal)
        
        self.status_bar = QLabel("Aguardando entrada...")
        self.status_bar.setObjectName("status_bar")
        
        view_layout.addLayout(h_views)
        view_layout.addWidget(self.status_bar)

        main_layout.addLayout(sidebar, 1)
        main_layout.addLayout(view_layout, 4)

        # Eventos
        self.btn_load_img.clicked.connect(self.load_image)
        self.btn_load_seeds.clicked.connect(self.load_seeds)
        self.btn_run.clicked.connect(self.run_dift)
        self.sld_z.valueChanged.connect(self.update_views)
        self.sld_y.valueChanged.connect(self.update_views)
        self.sld_x.valueChanged.connect(self.update_views)
        self.spin_brush.valueChanged.connect(self.update_brush)
        self.combo_label.currentIndexChanged.connect(self.update_label)

    # ... (Lógica de processamento similar ao seu original, mas organizada)

    def update_brush(self, val): self.brush_size = val
    def update_label(self, idx): self.current_label = idx + 1

    def sync_seeds_to_volume(self):
        # Como o ImageView edita a slice da seed diretamente, 
        # garantimos que o volume global 'self.seeds' reflita isso
        pass # No ImageView já fazemos a referência direta

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar SCN", "", "Arquivos SCN (*.scn)")
        if path:
            self.volume = read_scn(path)
            self.seeds = np.zeros_like(self.volume, dtype=np.uint8)
            z, y, x = self.volume.shape
            self.sld_z.setMaximum(z-1); self.sld_y.setMaximum(y-1); self.sld_x.setMaximum(x-1)
            self.state = "LOADED"
            self.status_bar.setText(f"Status: Volume carregado {x}x{y}x{z}")
            self.update_views()

    def load_seeds(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar Seeds", "", "Arquivos SCN (*.scn)")
        if path:
            self.seeds = read_scn(path)
            self.update_views()

    def normalize(self, img):
        mn, mx = img.min(), img.max()
        return ((img - mn) / (mx - mn + 1e-7) * 255).astype(np.uint8)

    def update_views(self):
        if not hasattr(self, 'volume'): return
        
        z, y, x = self.sld_z.value(), self.sld_y.value(), self.sld_x.value()
        
        # Axial
        ax_img = np.stack([self.normalize(self.volume[z,:,:])]*3, axis=-1)
        self.view_axial.set_image(ax_img)
        self.view_axial.set_overlay(self.seeds[z,:,:])
        
        # Coronal
        cor_img = np.stack([self.normalize(self.volume[:,y,:])]*3, axis=-1)
        self.view_coronal.set_image(cor_img)
        self.view_coronal.set_overlay(self.seeds[:,y,:])

        # Sagital
        sag_img = np.stack([self.normalize(self.volume[:,:,x])]*3, axis=-1)
        self.view_sagittal.set_image(sag_img)
        self.view_sagittal.set_overlay(self.seeds[:,:,x])

    def run_dift(self):
        if self.volume is None or self.seeds is None:
            self.set_status("Erro: Carregue a imagem e as seeds primeiro! ❌")
            return

        # 2. Bloqueio de UI e Feedback
        self.state = "RUNNING"
        self.btn_run.setEnabled(False)  # Evita cliques duplos
        self.set_status("Executando DIFT... Isso pode levar alguns segundos ⏳")
        
        # Força o Qt a atualizar o texto do status antes de entrar no processo pesado
        QApplication.processEvents()

        try:
            # 3. Preparação dos arquivos temporários
            img_path = os.path.join(TEMP_DIR, "img.scn")
            seed_path = os.path.join(TEMP_DIR, "seed.scn")

            self.set_status("Salvando arquivos temporários...")
            write_scn(img_path, self.volume)
            write_scn(seed_path, self.seeds)

            # 4. Execução do Binário DIFT
            # subprocess.run é síncrono, a interface vai esperar aqui
            self.set_status("Processando algoritmos no DIFT...")
            # result = subprocess.run(
            #     [DIFT_BIN, img_path, seed_path, TEMP_DIR, "true"],
            #     capture_output=True,
            #     text=True
            # )

            result = subprocess.run([
                "docker", "run", "--rm",
                "-v", f"{os.path.abspath(TEMP_DIR)}:/data",
                "dift-backend",
                "/data/img.scn",
                "/data/seed.scn",
                "/data/output.scn"
            ])

            # 5. Verificação de Saída
            result_path = os.path.join(TEMP_DIR, "seg-step-1.scn")

            if not os.path.exists(result_path):
                print(f"Erro no DIFT: {result.stderr}")
                self.set_status("Erro no processamento do binário ❌")
                self.btn_run.setEnabled(True)
                return

            # 6. Pós-processamento e Mapeamento de Labels
            self.set_status("Lendo resultado e mapeando labels...")
            new_seeds = read_scn(result_path)

            vals = np.unique(new_seeds)
            vals = vals[vals != 0]  # Ignora o que for zero (background absoluto)
            
            mapped = np.zeros_like(new_seeds, dtype=np.uint8)
            
            # Mapeia os labels encontrados para a nossa convenção interna
            for i, val in enumerate(vals):
                if i < 2:  # Limita aos nossos dois labels (objeto e fundo)
                    mapped[new_seeds == val] = (i + 1)

            self.seeds = mapped

            self.state = "RESULT_READY"
            self.set_status("Segmentação concluída com sucesso! ✅")
            self.update_views()

        except Exception as e:
            self.set_status(f"Erro inesperado: {str(e)} ❌")
            print(f"Detalhes do erro: {e}")
        
        finally:
            self.btn_run.setEnabled(True)
            self.state = "IDLE"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec())