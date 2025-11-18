#!/usr/bin/env python3
"""
cam_viewer_threaded_probe_fix.py

Versión mejorada del viewer:
 - Probe no bloqueante (no hace cap.read() durante probe).
 - Selección de backend por plataforma (mejora fiabilidad).
 - Botón "Cancelar búsqueda" y emisión de resultados parciales.
 - Uso de QThread para probe y video (no bloquea GUI).

Requisitos:
    pip install pyqt5 opencv-python numpy
"""

import sys
import time
import platform
import cv2
import numpy as np
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox,
    QHBoxLayout, QVBoxLayout, QMessageBox, QSpinBox
)

# ----- ProbeThread: no hace read() durante probe (evita bloqueos) -----
class ProbeThread(QThread):
    partial = pyqtSignal(list)  # emite resultados parciales
    finished = pyqtSignal(list)  # emite resultado final

    def __init__(self, max_index=8, delay_between=0.05, parent=None):
        super().__init__(parent)
        self.max_index = max_index
        self._stopped = False
        self.delay_between = delay_between
        self._backend = self._choose_backend()

    def _choose_backend(self):
        plat = platform.system().lower()
        # elegir backend según plataforma (mejora en muchos casos)
        if "windows" in plat:
            return cv2.CAP_DSHOW  # DirectShow suele ser rápido en Windows
        elif "linux" in plat:
            return cv2.CAP_V4L2  # Video4Linux2
        elif "darwin" in plat:
            return cv2.CAP_AVFOUNDATION  # macOS
        else:
            return cv2.CAP_ANY

    def run(self):
        devices = []
        # Intentar abrir cada índice, pero NO llamar a read() aquí.
        for i in range(0, self.max_index + 1):
            if self._stopped:
                break
            try:
                cap = cv2.VideoCapture(i, self._backend)
            except Exception:
                cap = cv2.VideoCapture(i, cv2.CAP_ANY)
            # Verificamos isOpened() rápidamente; no hacer read()
            if cap is not None and cap.isOpened():
                devices.append((i, f"Cámara {i}"))
                # Emitir parcial para que la UI se actualice mientras sigue probeando
                self.partial.emit(list(devices))
            # Liberar inmediatamente (no dejamos cap.read() bloquear)
            try:
                cap.release()
            except Exception:
                pass
            # Pequeña pausa para evitar saturar el bus USB/OS
            time.sleep(self.delay_between)
        # emitir final (puede ser igual al último parcial)
        self.finished.emit(list(devices))

    def stop(self):
        self._stopped = True


# ----- VideoThread: igual que antes, lee frames y los emite -----
class VideoThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    error = pyqtSignal(str)
    finished_open = pyqtSignal()

    def __init__(self, index, width=None, height=None, fps=20, parent=None):
        super().__init__(parent)
        self.index = int(index)
        self.width = width
        self.height = height
        self.fps = max(1, int(fps))
        self._running = True
        self.cap = None
        # intentar escoger backend adecuado también para abrir cámara
        plat = platform.system().lower()
        if "windows" in plat:
            self.backend = cv2.CAP_DSHOW
        elif "linux" in plat:
            self.backend = cv2.CAP_V4L2
        elif "darwin" in plat:
            self.backend = cv2.CAP_AVFOUNDATION
        else:
            self.backend = cv2.CAP_ANY

    def run(self):
        try:
            self.cap = cv2.VideoCapture(self.index, self.backend)
            if not self.cap.isOpened():
                self.error.emit(f"No se pudo abrir la cámara {self.index}")
                return

            if self.width and self.height:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.width))
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.height))

            self.finished_open.emit()
            interval_ms = int(1000 / self.fps)

            while self._running:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    self.error.emit("Falló la lectura del frame (posible desconexión).")
                    break
                self.frame_ready.emit(frame)
                self.msleep(max(1, interval_ms))
        except Exception as e:
            self.error.emit(f"Excepción en VideoThread: {e}")
        finally:
            try:
                if self.cap is not None:
                    self.cap.release()
            except Exception:
                pass

    def stop(self):
        self._running = False
        try:
            if self.cap is not None and self.cap.isOpened():
                self.cap.release()
        except Exception:
            pass
        self.wait(timeout=1000)


# ----- GUI principal -----
class CameraViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visor de Cámaras (probe no bloqueante)")
        self.video_thread = None
        self.probe_thread = None

        # Widgets
        self.video_label = QLabel("Selecciona una cámara y presiona Iniciar")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)

        self.device_combo = QComboBox()
        self.refresh_btn = QPushButton("Refrescar")
        self.cancel_probe_btn = QPushButton("Cancelar búsqueda")
        self.cancel_probe_btn.setEnabled(False)

        self.start_btn = QPushButton("Iniciar")
        self.stop_btn = QPushButton("Detener")
        self.stop_btn.setEnabled(False)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["Auto", "640x480", "1280x720", "1920x1080"])
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setValue(20)
        self.fps_spin.setSuffix(" FPS")

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.device_combo)
        top_layout.addWidget(self.refresh_btn)
        top_layout.addWidget(self.cancel_probe_btn)
        top_layout.addWidget(self.start_btn)
        top_layout.addWidget(self.stop_btn)
        top_layout.addWidget(self.resolution_combo)
        top_layout.addWidget(self.fps_spin)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.video_label)
        self.setLayout(main_layout)

        # Conexiones
        self.refresh_btn.clicked.connect(self.refresh_devices)
        self.cancel_probe_btn.clicked.connect(self.cancel_probe)
        self.start_btn.clicked.connect(self.start_camera)
        self.stop_btn.clicked.connect(self.stop_camera)

        # iniciar probe inicial
        self.refresh_devices()

    def refresh_devices(self):
        # Si un probe ya está corriendo, no iniciar otro
        if self.probe_thread is not None and self.probe_thread.isRunning():
            return
        self.device_combo.clear()
        self.device_combo.addItem("Buscando...", -1)
        self.cancel_probe_btn.setEnabled(True)
        self.refresh_btn.setEnabled(False)

        # iniciar probe no bloqueante
        self.probe_thread = ProbeThread(max_index=8, delay_between=0.04)
        self.probe_thread.partial.connect(self.on_probe_partial)
        self.probe_thread.finished.connect(self.on_probe_finished)
        self.probe_thread.start()

    def on_probe_partial(self, devices):
        # actualizar la lista con resultados parciales
        cur = self.device_combo.currentData()
        self.device_combo.clear()
        if not devices:
            self.device_combo.addItem("Buscando...", -1)
        else:
            for idx, name in devices:
                self.device_combo.addItem(name, idx)
            # Si había un item seleccionado intenta mantenerlo (si existe)
            if cur is not None:
                idxs = [d[0] for d in devices]
                if cur in idxs:
                    self.device_combo.setCurrentIndex(idxs.index(cur))

    def on_probe_finished(self, devices):
        self.cancel_probe_btn.setEnabled(False)
        self.refresh_btn.setEnabled(True)
        self.device_combo.clear()
        if not devices:
            self.device_combo.addItem("No se detectaron cámaras", -1)
        else:
            for idx, name in devices:
                self.device_combo.addItem(name, idx)

    def cancel_probe(self):
        if self.probe_thread is not None and self.probe_thread.isRunning():
            self.probe_thread.stop()
            # La señal finished se emitirá al terminar o puedes forzar limpieza:
            self.cancel_probe_btn.setEnabled(False)
            self.refresh_btn.setEnabled(True)
            # mantener el estado actual del combo (no borrar)
            # si estaba "Buscando...", reemplazar por instrucción
            if self.device_combo.count() == 1 and self.device_combo.itemText(0).startswith("Buscando"):
                self.device_combo.setItemText(0, "Búsqueda cancelada")

    def parse_resolution(self, text):
        if text == "Auto":
            return None, None
        try:
            w, h = text.split('x')
            return int(w), int(h)
        except Exception:
            return None, None

    def start_camera(self):
        data = self.device_combo.currentData()
        if data is None or data == -1:
            QMessageBox.warning(self, "Advertencia", "Selecciona una cámara válida.")
            return
        index = int(data)
        if self.video_thread is not None and self.video_thread.isRunning():
            QMessageBox.information(self, "Info", "La cámara ya está en ejecución.")
            return
        w, h = self.parse_resolution(self.resolution_combo.currentText())
        fps = self.fps_spin.value()
        self.video_thread = VideoThread(index=index, width=w, height=h, fps=fps)
        self.video_thread.frame_ready.connect(self.on_frame)
        self.video_thread.error.connect(self.on_video_error)
        self.video_thread.finished_open.connect(self.on_video_opened)
        self.video_thread.start()
        self.start_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.device_combo.setEnabled(False)

    def on_video_opened(self):
        self.stop_btn.setEnabled(True)

    def on_frame(self, frame_bgr):
        try:
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pix = QPixmap.fromImage(qt_image)
            scaled = pix.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.video_label.setPixmap(scaled)
        except Exception:
            pass

    def on_video_error(self, msg):
        QMessageBox.warning(self, "Error de cámara", msg)
        self.stop_camera()

    def stop_camera(self):
        if self.video_thread is not None:
            try:
                self.video_thread.stop()
            except Exception:
                pass
            try:
                self.video_thread.frame_ready.disconnect()
            except Exception:
                pass
            self.video_thread = None
        self.stop_btn.setEnabled(False)
        self.start_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.device_combo.setEnabled(True)
        self.video_label.setPixmap(QPixmap())
        self.video_label.setText("Selecciona una cámara y presiona Iniciar")

    def closeEvent(self, event):
        try:
            if self.probe_thread is not None and self.probe_thread.isRunning():
                self.probe_thread.stop()
                self.probe_thread.wait(timeout=500)
        except Exception:
            pass
        try:
            if self.video_thread is not None and self.video_thread.isRunning():
                self.video_thread.stop()
        except Exception:
            pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    viewer = CameraViewer()
    viewer.resize(900, 600)
    viewer.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
