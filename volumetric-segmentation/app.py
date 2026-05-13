import sys
import numpy as np
import subprocess
import os
import time

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QLabel, QSlider, QComboBox, QFrame, QGroupBox,
    QSpinBox, QSizePolicy, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar
)
from PyQt6.QtGui import QImage, QPixmap, QFont, QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QThread, pyqtSignal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIFT_BIN = os.path.abspath(os.path.join(BASE_DIR, "code/DIFT"))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

QSS = """
QWidget {
    background-color: #0a0c0f;
    color: #c8d8e8;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 12px;
}

#sidebar {
    background-color: #0d1117;
    border-right: 1px solid #1c2a38;
    min-width: 262px;
    max-width: 262px;
}

QGroupBox {
    border: 1px solid #1c2a38;
    border-radius: 6px;
    margin-top: 18px;
    padding: 12px 8px 8px 8px;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 2px;
    color: #4a7a9b;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px; top: -1px;
    padding: 0 4px;
    background-color: #0d1117;
}

QPushButton {
    background-color: #111922;
    border: 1px solid #1c2a38;
    border-radius: 4px;
    padding: 7px 12px;
    color: #7ab3d0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
}
QPushButton:hover  { background-color:#162130; border-color:#2e6fa3; color:#a8d8f0; }
QPushButton:pressed { background-color:#0e1a26; }
QPushButton:disabled { color:#2a3a4a; border-color:#141e28; }

QPushButton#btn_run {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #0e4a6e, stop:1 #0a3550);
    border: 1px solid #1a7ab5;
    color: #7ad4ff;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 1px;
    padding: 12px;
    border-radius: 6px;
}
QPushButton#btn_run:hover    { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #155e8a,stop:1 #0f4a6e); color:#aae8ff; }
QPushButton#btn_run:disabled { background:#111922; border-color:#1c2a38; color:#2a4a5a; }

QPushButton#btn_undo  { background:#1a1008; border-color:#5a3a10; color:#c89040; }
QPushButton#btn_undo:hover  { background:#241508; border-color:#c89040; }
QPushButton#btn_reset { background:#1a0808; border-color:#5a1010; color:#c84040; }
QPushButton#btn_reset:hover { background:#240808; border-color:#c84040; }

QSlider::groove:horizontal { height:3px; background:#1c2a38; border-radius:2px; }
QSlider::handle:horizontal {
    background:#2e7ab5; width:12px; height:12px;
    margin:-5px 0; border-radius:6px; border:1px solid #4a9ad4;
}
QSlider::sub-page:horizontal { background:#1a5a8a; border-radius:2px; }

QComboBox {
    background:#111922; border:1px solid #1c2a38;
    border-radius:4px; padding:5px 8px; color:#7ab3d0;
}
QComboBox::drop-down { border:none; width:20px; }
QComboBox QAbstractItemView {
    background:#111922; border:1px solid #2e6fa3;
    selection-background-color:#1a4a6a; color:#c8d8e8;
}

QSpinBox {
    background:#111922; border:1px solid #1c2a38;
    border-radius:4px; padding:4px 6px; color:#7ab3d0;
}

QLabel#status_bar {
    background:#080c10; border-top:1px solid #1c2a38;
    padding:5px 10px; color:#4a7a9b; font-size:11px;
}
QLabel#section_title { color:#2e7ab5; font-size:10px; letter-spacing:2px; font-weight:bold; }
QLabel#metric_value  { color:#7ad4ff; font-size:16px; font-weight:bold; }
QLabel#metric_label  { color:#4a7a9b; font-size:10px; letter-spacing:1px; }

QTabWidget::pane { border:1px solid #1c2a38; background:#0a0c0f; border-radius:4px; }
QTabBar::tab {
    background:#0d1117; border:1px solid #1c2a38; border-bottom:none;
    padding:6px 14px; color:#4a7a9b; font-size:11px;
}
QTabBar::tab:selected { background:#0a0c0f; border-top:2px solid #2e7ab5; color:#7ad4ff; }

QTableWidget { background:#0a0c0f; border:none; gridline-color:#1c2a38; color:#c8d8e8; }
QTableWidget::item:selected { background:#1a3a5a; }
QHeaderView::section {
    background:#0d1117; border:none; border-bottom:1px solid #1c2a38;
    padding:6px; color:#4a7a9b; font-size:10px; letter-spacing:1px;
}

QScrollBar:vertical { background:#0a0c0f; width:8px; border-radius:4px; }
QScrollBar::handle:vertical { background:#1c2a38; border-radius:4px; min-height:20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }

QProgressBar {
    background:#111922; border:1px solid #1c2a38;
    border-radius:3px; height:4px; text-align:center;
}
QProgressBar::chunk {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a7ab5,stop:1 #00c8a0);
    border-radius:3px;
}

QFrame[frameShape="4"], QFrame[frameShape="5"] { color:#1c2a38; }
"""

def read_scn_int(path):
    """Lê .scn com valores inteiros (label, pred, root, markers)."""
    with open(path, "rb") as f:
        magic = f.readline().decode().strip()
        if magic != "SCN":
            return None
        x, y, z = map(int, f.readline().decode().split())
        f.readline()                          # voxel size
        bits = int(f.readline().decode())
        dtype = {8: np.uint8, 16: np.uint16, 32: np.int32}.get(bits, np.uint16)
        raw = np.fromfile(f, dtype=dtype)
    if raw.size == x * y * z:
        return raw.reshape((z, y, x))
    return None

def write_scn(path, volume, bits=16):
    """Escreve .scn inteiro."""
    z, y, x = volume.shape
    dtype = {8: np.uint8, 16: np.uint16, 32: np.int32}[bits]
    with open(path, "wb") as f:
        f.write(b"SCN\n")
        f.write(f"{x} {y} {z}\n".encode())
        f.write(b"1.0 1.0 1.0\n")
        f.write(f"{bits}\n".encode())
        volume.astype(dtype).tofile(f)

def compute_metrics(seg, gt):
    s = (seg > 0).astype(np.uint8)
    g = (gt  > 0).astype(np.uint8)
    inter = np.logical_and(s, g).sum()
    dsc   = 2 * inter / (s.sum() + g.sum() + 1e-7)
    iou   = inter / (np.logical_or(s, g).sum() + 1e-7)
    try:
        from scipy.ndimage import binary_erosion
        from scipy.spatial.distance import cdist
        def surf(m):
            b = m & ~binary_erosion(m)
            return np.column_stack(np.where(b))
        ps, pg = surf(s.astype(bool)), surf(g.astype(bool))
        if len(ps) == 0 or len(pg) == 0:
            hd95 = float("nan")
        else:
            if len(ps) > 2000: ps = ps[np.random.choice(len(ps), 2000, replace=False)]
            if len(pg) > 2000: pg = pg[np.random.choice(len(pg), 2000, replace=False)]
            D = cdist(ps, pg)
            hd95 = max(np.percentile(D.min(1), 95), np.percentile(D.min(0), 95))
    except Exception:
        hd95 = float("nan")
    return {"DSC": float(dsc), "IoU": float(iou), "HD95": float(hd95)}

class DIFTWorker(QThread):
    finished = pyqtSignal(float)
    error    = pyqtSignal(str)

    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd

    def run(self):
        t0 = time.time()
        try:
            r = subprocess.run(self.cmd, capture_output=True, text=True, timeout=300)
            elapsed = time.time() - t0
            if r.returncode != 0:
                self.error.emit(r.stderr or "Erro desconhecido no binário.")
            else:
                self.finished.emit(elapsed)
        except subprocess.TimeoutExpired:
            self.error.emit("Timeout: DIFT demorou mais de 5 minutos.")
        except Exception as e:
            self.error.emit(str(e))

class SliceView(QLabel):
    seedPainted = pyqtSignal()

    COLORS = {1: (255, 80, 60), 2: (60, 160, 255)}

    def __init__(self, axis, app_ref):
        super().__init__()
        self.axis = axis
        self.app  = app_ref
        self.base = None
        self.seg  = None
        self.seed = None
        self._drawing = False
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background:#060809; border:1px solid #1c2a38; border-radius:4px;"
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(180, 180)

    def set_data(self, base, seg=None, seed=None):
        self.base = base
        self.seg  = seg
        self.seed = seed
        self._repaint()

    def _repaint(self):
        if self.base is None:
            return
        img = self.base.copy()
        if self.seg is not None:
            for lbl, col in self.COLORS.items():
                if lbl == 2:
                    continue
                m = self.seg == lbl
                img[m] = (img[m] * 0.45 + np.array(col) * 0.55).astype(np.uint8)
        if self.seed is not None:
            for lbl, col in self.COLORS.items():
                img[self.seed == lbl] = col

        h, w = img.shape[:2]
        qi = QImage(img.tobytes(), w, h, 3 * w, QImage.Format.Format_RGB888)
        pm = QPixmap.fromImage(qi).scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter = QPainter(pm)
        painter.setPen(QPen(QColor("#2e7ab5")))
        painter.setFont(QFont("JetBrains Mono", 9, QFont.Weight.Bold))
        painter.drawText(8, 18, self.axis)
        painter.end()
        self.setPixmap(pm)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._repaint()

    def _to_img(self, pos):
        pm = self.pixmap()
        if pm is None or self.base is None:
            return None, None
        pw, ph = pm.width(), pm.height()
        ox = (self.width()  - pw) / 2
        oy = (self.height() - ph) / 2
        rx = (pos.x() - ox) / pw
        ry = (pos.y() - oy) / ph
        if not (0 <= rx <= 1 and 0 <= ry <= 1):
            return None, None
        H, W = self.base.shape[:2]
        return int(ry * H), int(rx * W)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drawing = True
            self._paint(e.position())

    def mouseMoveEvent(self, e):
        if self._drawing:
            self._paint(e.position())

    def mouseReleaseEvent(self, e):
        self._drawing = False

    def _paint(self, pos):
        if self.seed is None or self.app.is_running:
            return
        r, c = self._to_img(pos)
        if r is None:
            return
        b = self.app.brush_size
        lbl = self.app.current_label
        H, W = self.seed.shape
        rr = np.arange(max(0, r - b), min(H, r + b + 1))
        cc = np.arange(max(0, c - b), min(W, c + b + 1))
        rg, cg = np.meshgrid(rr - r, cc - c, indexing="ij")
        disk = rg ** 2 + cg ** 2 <= b ** 2
        r0, r1 = max(0, r - b), min(H, r + b + 1)
        c0, c1 = max(0, c - b), min(W, c + b + 1)
        self.seed[r0:r1, c0:c1][disk] = lbl
        self._repaint()
        self.seedPainted.emit()

class MetricCard(QFrame):
    def __init__(self, name, unit=""):
        super().__init__()
        self.setStyleSheet(
            "QFrame{background:#0d1117;border:1px solid #1c2a38;"
            "border-radius:6px;padding:6px;}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(2)
        self.val = QLabel("—")
        self.val.setObjectName("metric_value")
        self.val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(name + (f" [{unit}]" if unit else ""))
        lbl.setObjectName("metric_label")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.val)
        lay.addWidget(lbl)

    def set(self, v, fmt=".4f"):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            self.val.setText("—")
        else:
            self.val.setText(format(v, fmt) if isinstance(v, float) else str(v))

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DIFT  ·  Interactive Segmentation")
        self.resize(1440, 860)
        self.setStyleSheet(QSS)

        self.volume    : np.ndarray | None = None
        self.init_seg  : np.ndarray | None = None
        self.gt_seg    : np.ndarray | None = None
        self.seeds     : np.ndarray | None = None
        self.cur_label : np.ndarray | None = None
        self.img_path  = ""
        self.step      = 0
        self.brush_size    = 3
        self.current_label = 1
        self.is_running    = False
        self.history       = []

        self._build_ui()
        self._connect()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sb_widget = QWidget()
        sb_widget.setObjectName("sidebar")
        sb = QVBoxLayout(sb_widget)
        sb.setContentsMargins(12, 14, 12, 12)
        sb.setSpacing(10)

        title = QLabel("DIFT")
        title.setStyleSheet(
            "color:#2e7ab5;font-size:22px;font-weight:bold;letter-spacing:4px;"
        )
        sub = QLabel("Differential Image Foresting Transform")
        sub.setStyleSheet("color:#2a4a6a;font-size:9px;letter-spacing:1px;")
        sb.addWidget(title)
        sb.addWidget(sub)
        sb.addWidget(self._sep())

        grp_f = QGroupBox("ARQUIVOS")
        gf = QVBoxLayout(grp_f)
        gf.setSpacing(5)
        self.btn_img = QPushButton("📂  Volume (.scn)")
        self.btn_seg = QPushButton("🧠  Seg. Inicial (.scn)")
        self.btn_gt  = QPushButton("📐  Ground Truth  (opcional)")
        self.lbl_img = QLabel("—"); self.lbl_img.setStyleSheet("color:#2a4a6a;font-size:10px;")
        self.lbl_seg = QLabel("—"); self.lbl_seg.setStyleSheet("color:#2a4a6a;font-size:10px;")
        for w in [self.btn_img, self.lbl_img, self.btn_seg, self.lbl_seg, self.btn_gt]:
            gf.addWidget(w)
        sb.addWidget(grp_f)

        grp_t = QGroupBox("FERRAMENTAS")
        gt_lay = QVBoxLayout(grp_t)
        gt_lay.setSpacing(6)
        lbl_l = QLabel("Label ativo"); lbl_l.setObjectName("section_title")
        self.combo_label = QComboBox()
        self.combo_label.addItems(["● Objeto  (vermelho)", "● Fundo   (azul)"])
        lbl_b = QLabel("Tamanho do pincel"); lbl_b.setObjectName("section_title")
        self.spin_brush = QSpinBox()
        self.spin_brush.setRange(1, 60); self.spin_brush.setValue(3)
        self.btn_clear = QPushButton("✕  Limpar marcadores")
        for w in [lbl_l, self.combo_label, lbl_b, self.spin_brush, self.btn_clear]:
            gt_lay.addWidget(w)
        sb.addWidget(grp_t)

        grp_n = QGroupBox("NAVEGAÇÃO 3D")
        gn = QVBoxLayout(grp_n)
        gn.setSpacing(4)
        self.sld = {}; self.sld_lbl = {}
        for key, name in [("Z", "Z  axial"), ("Y", "Y  coronal"), ("X", "X  sagital")]:
            sld = QSlider(Qt.Orientation.Horizontal); sld.setMinimum(0); sld.setValue(0)
            lbl = QLabel(f"{name}:  0"); lbl.setObjectName("section_title")
            gn.addWidget(lbl); gn.addWidget(sld)
            self.sld[key] = sld; self.sld_lbl[key] = lbl
        sb.addWidget(grp_n)

        sb.addStretch()
        sb.addWidget(self._sep())

        row_btns = QHBoxLayout()
        self.btn_undo  = QPushButton("↩  Desfazer"); self.btn_undo.setObjectName("btn_undo")
        self.btn_reset = QPushButton("⊗  Resetar");  self.btn_reset.setObjectName("btn_reset")
        row_btns.addWidget(self.btn_undo); row_btns.addWidget(self.btn_reset)
        sb.addLayout(row_btns)

        self.btn_run = QPushButton("▶  EXECUTAR DIFT")
        self.btn_run.setObjectName("btn_run")
        self.btn_run.setMinimumHeight(48)
        sb.addWidget(self.btn_run)

        main_w = QWidget()
        ma = QVBoxLayout(main_w)
        ma.setContentsMargins(12, 12, 12, 0)
        ma.setSpacing(8)

        self.tabs = QTabWidget()

        tab_v = QWidget()
        tv = QVBoxLayout(tab_v)
        tv.setContentsMargins(4, 8, 4, 4)
        tv.setSpacing(6)

        views_row = QHBoxLayout(); views_row.setSpacing(6)
        self.view_z = SliceView("AXIAL",   self)
        self.view_y = SliceView("CORONAL", self)
        self.view_x = SliceView("SAGITAL", self)
        for v in (self.view_z, self.view_y, self.view_x):
            views_row.addWidget(v)
        tv.addLayout(views_row, stretch=1)

        metrics_row = QHBoxLayout(); metrics_row.setSpacing(8)
        self.c_dsc  = MetricCard("DSC")
        self.c_iou  = MetricCard("IoU")
        self.c_hd95 = MetricCard("HD95", "mm")
        self.c_time = MetricCard("Tempo", "s")
        self.c_step = MetricCard("Iteração")
        for c in (self.c_dsc, self.c_iou, self.c_hd95, self.c_time, self.c_step):
            metrics_row.addWidget(c)
        tv.addLayout(metrics_row)
        self.tabs.addTab(tab_v, "  Visualização  ")

        tab_h = QWidget()
        th = QVBoxLayout(tab_h)
        th.setContentsMargins(4, 8, 4, 4)
        th.setSpacing(8)
        self.hist_table = QTableWidget(0, 5)
        self.hist_table.setHorizontalHeaderLabels(
            ["Iteração", "Tempo (s)", "DSC", "IoU", "HD95 (mm)"]
        )
        self.hist_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.hist_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.hist_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        th.addWidget(self.hist_table)
        self.btn_restore = QPushButton("↩  Restaurar iteração selecionada")
        th.addWidget(self.btn_restore)
        self.tabs.addTab(tab_h, "  Histórico  ")

        ma.addWidget(self.tabs, stretch=1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        self.progress.setMaximumHeight(4)
        ma.addWidget(self.progress)

        self.status_bar = QLabel("Aguardando volume…")
        self.status_bar.setObjectName("status_bar")
        ma.addWidget(self.status_bar)

        root.addWidget(sb_widget)
        root.addWidget(main_w, stretch=1)

    def _sep(self):
        f = QFrame(); f.setFrameShape(QFrame.Shape.HLine); return f

    def _connect(self):
        self.btn_img.clicked.connect(self._load_image)
        self.btn_seg.clicked.connect(self._load_seg)
        self.btn_gt.clicked.connect(self._load_gt)
        self.btn_run.clicked.connect(self._run_dift)
        self.btn_undo.clicked.connect(self._undo)
        self.btn_reset.clicked.connect(self._reset)
        self.btn_clear.clicked.connect(self._clear_seeds)
        self.btn_restore.clicked.connect(self._restore_selected)
        self.combo_label.currentIndexChanged.connect(
            lambda i: setattr(self, "current_label", i + 1)
        )
        self.spin_brush.valueChanged.connect(
            lambda v: setattr(self, "brush_size", v)
        )
        for sld in self.sld.values():
            sld.valueChanged.connect(self._on_slider)
        for v in (self.view_z, self.view_y, self.view_x):
            v.seedPainted.connect(self._update_views)
        self.hist_table.cellDoubleClicked.connect(self._restore_selected)

    def _status(self, msg, color="#4a7a9b"):
        self.status_bar.setText(msg)
        self.status_bar.setStyleSheet(
            f"background:#080c10;border-top:1px solid #1c2a38;"
            f"padding:5px 10px;color:{color};font-size:11px;"
        )
        QApplication.processEvents()

    def _load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Volume", "", "SCN (*.scn)")
        if not path: return
        vol = read_scn_int(path)
        if vol is None:
            self._status("❌  Falha ao ler volume.", "#c84040"); return
        self.volume   = vol
        self.img_path = path
        self.seeds    = np.zeros_like(vol, dtype=np.uint8)
        self.cur_label = None
        z, y, x = vol.shape
        maxs = {"Z": z-1, "Y": y-1, "X": x-1}
        mids = {"Z": z//2, "Y": y//2, "X": x//2}
        for k, sld in self.sld.items():
            sld.setMaximum(maxs[k]); sld.setValue(mids[k])
        self.lbl_img.setText(os.path.basename(path))
        self._status(f"✓  Volume {x}×{y}×{z}", "#00c8a0")
        self._update_views()

    def _load_seg(self):
        path, _ = QFileDialog.getOpenFileName(self, "Segmentação Inicial", "", "SCN (*.scn)")
        if not path: return
        seg = read_scn_int(path)
        if seg is None:
            self._status("❌  Falha ao ler segmentação.", "#c84040"); return
        self.init_seg  = seg
        self.cur_label = seg.copy()
        self.lbl_seg.setText(os.path.basename(path))
        self._status("✓  Segmentação inicial carregada.", "#00c8a0")
        self._update_views()

    def _load_gt(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ground Truth", "", "SCN (*.scn)")
        if not path: return
        gt = read_scn_int(path)
        if gt is None:
            self._status("❌  Falha ao ler ground truth.", "#c84040"); return
        self.gt_seg = gt
        self._status("✓  Ground truth carregado.", "#00c8a0")

    def _norm(self, a):
        mn, mx = a.min(), a.max()
        if mx == mn: return np.zeros_like(a, dtype=np.uint8)
        return ((a - mn) / (mx - mn) * 255).astype(np.uint8)

    def _on_slider(self):
        for k, sld in self.sld.items():
            names = {"Z": "Z  axial", "Y": "Y  coronal", "X": "X  sagital"}
            self.sld_lbl[k].setText(f"{names[k]}:  {sld.value()}")
        self._update_views()

    def _update_views(self):
        if self.volume is None: return
        z = self.sld["Z"].value()
        y = self.sld["Y"].value()
        x = self.sld["X"].value()

        for key, view, sl_vol, sl_seg, sl_seed in [
            ("Z", self.view_z,
             self.volume[z, :, :],
             self.cur_label[z, :, :] if self.cur_label is not None else None,
             self.seeds[z, :, :]     if self.seeds is not None else None),
            ("Y", self.view_y,
             self.volume[:, y, :],
             self.cur_label[:, y, :] if self.cur_label is not None else None,
             self.seeds[:, y, :]     if self.seeds is not None else None),
            ("X", self.view_x,
             self.volume[:, :, x],
             self.cur_label[:, :, x] if self.cur_label is not None else None,
             self.seeds[:, :, x]     if self.seeds is not None else None),
        ]:
            g = self._norm(sl_vol)
            base = np.stack([g, g, g], axis=-1)
            view.set_data(base, sl_seg, sl_seed)

    def _clear_seeds(self):
        if self.seeds is not None:
            self.seeds[:] = 0
            self._update_views()

    def _undo(self):
        if len(self.history) < 2:
            self._status("Nenhuma iteração anterior.", "#c89040"); return
        self.history.pop()
        prev = self.history[-1]
        self._load_label(prev["label_path"])
        self.step = prev["step"]
        self._update_cards(prev)
        self._status(f"↩  Desfeito para iteração {self.step}.", "#c89040")

    def _reset(self):
        self.step = 0; self.history.clear()
        self.hist_table.setRowCount(0)
        if self.init_seg is not None: self.cur_label = self.init_seg.copy()
        if self.seeds    is not None: self.seeds[:] = 0
        self._update_views()
        self._status("⊗  Resetado.", "#c84040")

    def _run_dift(self):
        if self.volume is None or self.init_seg is None:
            self._status("❌  Carregue volume e segmentação.", "#c84040"); return
        if self.step > 0 and np.all(self.seeds == 0):
            self._status("⚠  Adicione marcadores antes de executar.", "#c89040"); return

        self.is_running = True
        self.btn_run.setEnabled(False)
        self.progress.setVisible(True)

        img_path    = os.path.join(TEMP_DIR, "img.scn")
        seg_path    = os.path.join(TEMP_DIR, "init_seg.scn")
        marker_path = os.path.join(TEMP_DIR, "markers.scn")

        write_scn(img_path, self.volume.astype(np.int32),   bits=16)
        write_scn(seg_path, self.init_seg.astype(np.int32), bits=16)

        if self.step == 0:
            cmd = [DIFT_BIN, img_path, seg_path, TEMP_DIR]
            self._status("▶  Executando DIFT — passo inicial…", "#2e7ab5")
        else:
            write_scn(marker_path, self.seeds.astype(np.int32), bits=16)
            prev_dir   = os.path.join(TEMP_DIR, f"step-{self.step}")
            next_step  = self.step + 1
            cmd = [
                DIFT_BIN,
                img_path, seg_path, TEMP_DIR,
                prev_dir, marker_path, str(next_step),
            ]
            self._status(f"▶  Executando DIFT — passo {next_step}…", "#2e7ab5")

        self._worker = DIFTWorker(cmd)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, elapsed):
        self.step += 1
        label_path = os.path.join(TEMP_DIR, f"step-{self.step}", "label_out.scn")
        if not os.path.exists(label_path):
            self._on_error(f"label_out.scn não encontrado em step-{self.step}/"); return

        self._load_label(label_path)
        if self.seeds is not None: self.seeds[:] = 0

        metrics = {}
        if self.gt_seg is not None and self.cur_label is not None:
            metrics = compute_metrics(self.cur_label, self.gt_seg)

        entry = {"step": self.step, "label_path": label_path,
                 "time": elapsed, "metrics": metrics}
        self.history.append(entry)
        self._add_hist_row(entry)
        self._update_cards(entry)
        self._finish()
        self._status(f"✓  Passo {self.step} concluído em {elapsed:.1f}s", "#00c8a0")

    def _on_error(self, msg):
        self._finish()
        self._status(f"❌  {msg}", "#c84040")

    def _finish(self):
        self.is_running = False
        self.btn_run.setEnabled(True)
        self.progress.setVisible(False)
        self._update_views()

    def _load_label(self, path):
        seg = read_scn_int(path)
        if seg is not None:
            self.cur_label = seg
            self._update_views()

    def _add_hist_row(self, e):
        row = self.hist_table.rowCount()
        self.hist_table.insertRow(row)
        m = e.get("metrics", {})
        def cell(v):
            it = QTableWidgetItem(v)
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            return it
        self.hist_table.setItem(row, 0, cell(str(e["step"])))
        self.hist_table.setItem(row, 1, cell(f"{e['time']:.2f}"))
        self.hist_table.setItem(row, 2, cell(f"{m['DSC']:.4f}"  if m else "—"))
        self.hist_table.setItem(row, 3, cell(f"{m['IoU']:.4f}"  if m else "—"))
        self.hist_table.setItem(row, 4, cell(f"{m['HD95']:.2f}" if m else "—"))
        self.hist_table.scrollToBottom()

    def _update_cards(self, e):
        m = e.get("metrics", {})
        self.c_dsc .set(m.get("DSC"))
        self.c_iou .set(m.get("IoU"))
        self.c_hd95.set(m.get("HD95"), ".2f")
        self.c_time.set(e.get("time"), ".2f")
        self.c_step.set(e.get("step"), "d")

    def _restore_selected(self, *_):
        row = self.hist_table.currentRow()
        if row < 0 or row >= len(self.history): return
        e = self.history[row]
        self._load_label(e["label_path"])
        self.step = e["step"]
        self._update_cards(e)
        self._status(f"↩  Restaurado: iteração {self.step}", "#c89040")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("JetBrains Mono", 11))
    win = App()
    win.show()
    sys.exit(app.exec())