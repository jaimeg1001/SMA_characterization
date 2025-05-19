import sys
import os
import cv2
import cv2.aruco as aruco
import json
import serial
import serial.tools.list_ports
import time
import csv
import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QPushButton, QComboBox, QTabWidget, QTextEdit,
                           QSpinBox, QFileDialog, QMessageBox, QGridLayout, QSplitter,
                           QFrame, QGroupBox, QDoubleSpinBox, QInputDialog, QDialog, QVBoxLayout,
                           QDialogButtonBox,QLineEdit)
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QSize, QThread, pyqtSignal
import numpy as np

class VideoCapture(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray, int)
    
    def __init__(self, camera_id):
        super().__init__()
        self.camera_id = camera_id
        self.running = True
        
    def run(self):
              
        if self.camera_id == 0:
            cap = self.init_videocapture(1024,576)
            cap.set(cv2.CAP_PROP_SETTINGS,1)
        else:
            cap = cv2.VideoCapture(self.camera_id,cv2.CAP_DSHOW)
        #if self.camera_id == 0:
        #    cap.set(cv2.CAP_PROP_SETTINGS,1)
        
        if not cap.isOpened():
            print(f"Error: No se pudo abrir la cámara {self.camera_id}")
            return
            
        while self.running:
            ret, frame = cap.read()
            if ret:
                self.change_pixmap_signal.emit(frame, self.camera_id)
            #time.sleep(0.03)  # Limitar la velocidad de captura
            
        cap.release()
    
    def init_videocapture(self,width, height):
        camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('M', 'J', 'P', 'G'))
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        return camera

    def stop(self):
        self.running = False
        self.wait()
        
class SerialThread(QThread):
    received_data_signal = pyqtSignal(str)
    connection_status_signal = pyqtSignal(bool, str)
    json_data_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.running = False
        
    def connect_serial(self, port, baudrate):
        try:
            self.serial_port = serial.Serial(port, baudrate, timeout=1)
            self.connection_status_signal.emit(True, f"Conexión establecida en {port} a {baudrate} baudios")
            self.running = True
            return True
        except Exception as e:
            self.connection_status_signal.emit(False, f"Error al conectar: {str(e)}")
            return False
            
    def run(self):
        while self.running and self.serial_port:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.readline().decode('utf-8').strip()
                    self.received_data_signal.emit(data)
                    
                    # Intentar procesar como JSON
                    try:
                        json_data = json.loads(data)
                        self.json_data_signal.emit(json_data)
                    except json.JSONDecodeError:
                        pass
                        
            except Exception as e:
                self.received_data_signal.emit(f"Error: {str(e)}")
                break
                
            time.sleep(0.01)
            
    def write_data(self, data):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(data.encode())
                return True
            except Exception as e:
                self.received_data_signal.emit(f"Error al enviar datos: {str(e)}")
                return False
        return False
        
    def stop(self):
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.wait()


class SMACharacterizationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Instituto Politécnico Nacional - Caracterización de SMA")
        self.setGeometry(100, 100, 1200, 800)
        
        self.force_offset = 0.0
        self.force_scale = 1.0
        self.known_force_raw = None
        self.force_offset_relay = 0.0
        self.force_scale_relay = 1.0
        self.relay_state = False  # False = OFF, True = ON
        self.experiment_running = False
        self.serial_connected = False
        self.arduino_validated = False
        self.experiment_finished = True

        # Aruco Functionality (test)
        self.aruco_detection = False
        self.aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        self.aruco_parameters = aruco.DetectorParameters()
        # Detect the markers in the image
        self.aruco_detector = aruco.ArucoDetector(self.aruco_dict, self.aruco_parameters)
        self.distance_Y = 0.0
        self.zero_deformation = 0.0


        self.debug = False
        self.data_folder = ""
        self.current_timestamp = ""
        self.camera_threads = []

        # Test para guardar imagenes
        self.lastFrames = [None,None]
        
        # Inicializar serial thread
        self.serial_thread = SerialThread()
        self.serial_thread.received_data_signal.connect(self.on_data_received)
        self.serial_thread.connection_status_signal.connect(self.on_connection_status)
        self.serial_thread.json_data_signal.connect(self.on_json_data_received)
        
        # Configurar la interfaz
        self.setup_ui()
        
        # Iniciar captura de cámaras
        self.init_cameras()
        
        self.create_calibration_directory()
        # Timer para actualizar la UI
        #self.update_timer = QTimer(self)
        #self.update_timer.timeout.connect(self.update_ui)
        #self.update_timer.start(50)  # Actualizar cada 50ms
        
    def setup_ui(self):
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        
        # Header con título e imágenes
        header_layout = QHBoxLayout()
        
        # Logo IPN (placeholder para imagen real)
        ipn_label = QLabel()
        ipn_pixmap = QPixmap("ipn.png")
        if ipn_pixmap.isNull():
            ipn_label.setText("ipn.png")
        else:
            ipn_label.setPixmap(ipn_pixmap.scaled(100, 100, Qt.KeepAspectRatio))
        ipn_label.setFixedSize(100, 100)
        header_layout.addWidget(ipn_label)
        
        # Título centrado
        title_label = QLabel("Instituto Politécnico Nacional\nCaracterización de SMA")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label, 1)
        
        # Logo CIDETEC (placeholder para imagen real)
        cidetec_label = QLabel()
        cidetec_pixmap = QPixmap("cidetec.png")
        if cidetec_pixmap.isNull():
            cidetec_label.setText("cidetec.png")
        else:
            cidetec_label.setPixmap(cidetec_pixmap.scaled(100, 100, Qt.KeepAspectRatio))
        cidetec_label.setFixedSize(100, 100)
        header_layout.addWidget(cidetec_label)
        
        main_layout.addLayout(header_layout)
        
        # Panel de cámaras
        cameras_layout = QHBoxLayout()
        
        # Cámara 1
        camera1_group = QGroupBox("Cámara 1")
        camera1_layout = QVBoxLayout(camera1_group)
        self.camera1_label = QLabel()
        self.camera1_label.setMinimumSize(320, 240)
        self.camera1_label.setAlignment(Qt.AlignCenter)
        self.camera1_label.setStyleSheet("background-color: black;")
        camera1_layout.addWidget(self.camera1_label)
        cameras_layout.addWidget(camera1_group)
        
        # Cámara 2
        camera2_group = QGroupBox("Cámara 2")
        camera2_layout = QVBoxLayout(camera2_group)
        self.camera2_label = QLabel()
        self.camera2_label.setMinimumSize(320, 240)
        self.camera2_label.setAlignment(Qt.AlignCenter)
        self.camera2_label.setStyleSheet("background-color: black;")
        camera2_layout.addWidget(self.camera2_label)
        cameras_layout.addWidget(camera2_group)
        
        main_layout.addLayout(cameras_layout)

        # Panel de conexión serial
        serial_group = QGroupBox("Conexión Serial")
        serial_layout = QGridLayout(serial_group)
        
        # Selección del puerto Serial
        serial_layout.addWidget(QLabel("Puerto:"), 0, 0)
        self.port_combo = QComboBox()
        serial_layout.addWidget(self.port_combo, 0, 1) 

        # Selección velocidad de comunicación
        serial_layout.addWidget(QLabel("Velocidad:"), 0, 2)
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baudrate_combo.setCurrentText("115200")
        serial_layout.addWidget(self.baudrate_combo, 0, 3)       

        # Actualizar Puertos Seriales
        self.refresh_btn = QPushButton("Actualizar puertos")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        serial_layout.addWidget(self.refresh_btn, 0, 4)

        # Boton para iniciar comunicaciín
        self.connect_btn = QPushButton("Iniciar comunicación")
        self.connect_btn.clicked.connect(self.toggle_connection)
        serial_layout.addWidget(self.connect_btn, 0, 5)
        
        # Boton para validar comunicación
        self.validate_btn = QPushButton("Validar comunicación")
        self.validate_btn.clicked.connect(self.validate_connection)
        serial_layout.addWidget(self.validate_btn, 0, 6)

        # Boton para borrar terminal
        self.clear_terminal_btn = QPushButton("Borrar terminal")
        self.clear_terminal_btn.clicked.connect(self.clear_terminal)
        serial_layout.addWidget(self.clear_terminal_btn, 0, 7)

        main_layout.addWidget(serial_group)

        # Terminal y pestañas inferiores
        bottom_splitter = QSplitter(Qt.Vertical)
        # Terminal
        terminal_group = QGroupBox("Terminal")
        terminal_layout = QVBoxLayout(terminal_group)
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")
        terminal_layout.addWidget(self.terminal)
        bottom_splitter.addWidget(terminal_group)

        # Pestañas
        self.tabs = QTabWidget()
        
        # Tab 1: Configuración del experimento
        experiment_tab = QWidget()
        experiment_layout = QGridLayout(experiment_tab)
        
        experiment_layout.addWidget(QLabel("Tiempo activo (ms):"), 0, 0)
        self.active_time_spin = QSpinBox()
        self.active_time_spin.setRange(1, 60000)
        self.active_time_spin.setValue(1000)
        experiment_layout.addWidget(self.active_time_spin, 0, 1)
        
        experiment_layout.addWidget(QLabel("Tiempo en reposo (ms):"), 1, 0)
        self.rest_time_spin = QSpinBox()
        self.rest_time_spin.setRange(1, 60000)
        self.rest_time_spin.setValue(1000)
        experiment_layout.addWidget(self.rest_time_spin, 1, 1)
        
        experiment_layout.addWidget(QLabel("Carpeta de datos:"), 2, 0)
        self.folder_layout = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setMaximumHeight(30)
        self.folder_edit.setReadOnly(True)
        self.folder_layout.addWidget(self.folder_edit)
        
        self.browse_btn = QPushButton("Examinar...")
        self.browse_btn.clicked.connect(self.browse_folder)
        self.folder_layout.addWidget(self.browse_btn)
        experiment_layout.addLayout(self.folder_layout, 2, 1, 1, 2)
        
        self.start_experiment_btn = QPushButton("Iniciar experimento")
        self.start_experiment_btn.clicked.connect(self.toggle_experiment)
        self.start_experiment_btn.setEnabled(False)
        experiment_layout.addWidget(self.start_experiment_btn, 3, 0, 1, 3)
        
        self.tabs.addTab(experiment_tab, "Configuración de experimento")

        # Tab 2: Calibración
        calibration_tab = QWidget()
        calibration_layout = QGridLayout(calibration_tab)
        
        # Lecturas de sensores
        readings_group = QGroupBox("Lecturas de sensores")
        readings_layout = QGridLayout(readings_group)
        
        readings_layout.addWidget(QLabel("Corriente (mA):"), 0, 0)
        self.current_label = QLabel("0.000")
        readings_layout.addWidget(self.current_label, 0, 1)
        
        readings_layout.addWidget(QLabel("Fuerza (N):"), 1, 0)
        self.force_label = QLabel("0.000")
        readings_layout.addWidget(self.force_label, 1, 1)
        
        readings_layout.addWidget(QLabel("Voltaje SMA (V):"), 2, 0)
        self.voltage_sma_label = QLabel("0.000")
        readings_layout.addWidget(self.voltage_sma_label, 2, 1)
        
        readings_layout.addWidget(QLabel("Voltaje referencia (V):"), 3, 0)
        self.voltage_ref_label = QLabel("0.000")
        readings_layout.addWidget(self.voltage_ref_label, 3, 1)

        readings_layout.addWidget(QLabel("Distance (mm):"), 4, 0)
        self.distance_label = QLabel("0.000")
        readings_layout.addWidget(self.distance_label, 4, 1)
        
        calibration_layout.addWidget(readings_group, 0, 0, 5, 1)
        
        # Botones de calibración
        self.debug_sensor_btn = QPushButton("Leer Sensores")
        self.debug_sensor_btn.clicked.connect(self.debug_sensores)
        calibration_layout.addWidget(self.debug_sensor_btn, 0, 1)


        self.calibrate_force_combined_btn = QPushButton("Calibrar sensor de fuerza")
        self.calibrate_force_combined_btn.clicked.connect(self.show_force_calibration_dialog)
        self.calibrate_force_combined_btn.setEnabled(False)
        calibration_layout.addWidget(self.calibrate_force_combined_btn, 1, 1)
            

        self.toggle_relay_btn = QPushButton("Activar relevador")
        self.toggle_relay_btn.clicked.connect(self.toggle_relay)
        self.relay_active = False
        self.toggle_relay_btn.setEnabled(False)
        calibration_layout.addWidget(self.toggle_relay_btn, 2, 1)

        self.capture_deformation_btn = QPushButton("Calibrar Deformación")
        self.capture_deformation_btn.clicked.connect(self.capture_zero_deformation)
        self.capture_deformation_btn.setEnabled(False)
        calibration_layout.addWidget(self.capture_deformation_btn, 3, 1)

        self.toggle_aruco = QPushButton("Detectar Arucos")
        self.toggle_aruco.clicked.connect(self.toggle_aruco_detection)
        calibration_layout.addWidget(self.toggle_aruco, 4, 1)

        calibration_layout.setRowStretch(5, 1)
        
        self.tabs.addTab(calibration_tab, "Calibración")


        bottom_splitter.addWidget(self.tabs)

        main_layout.addWidget(bottom_splitter, 1)

        # Establecer estilo global
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #444444;
                color: #FFFFFF;
            }
            QGroupBox {
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QLabel {
                color: #FFFFFF;
            }
        """)

        # Inicializar puertos
        self.refresh_ports()

    def init_cameras(self):
        # Iniciar captura de las cámaras
        for i in range(2):
            thread = VideoCapture(i)
            thread.change_pixmap_signal.connect(self.update_camera)
            thread.start()
            self.camera_threads.append(thread)
            
    def update_camera(self, image, camera_id):
        # Aruco functionalities (test)
        if camera_id == 0:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # Detect the markers in the image
            corners, ids, rejected = self.aruco_detector.detectMarkers(gray)
            if self.aruco_detection:
                aruco.drawDetectedMarkers(image, corners, ids)
            #--------------Calculo de la distancia---------------------------
            # Constants
            arucoWidth_mm = 20
            arucoHeight_mm = 20 

            if ids is not None:
                if np.array_equal(ids.flatten(),np.array([0,1])):
                    x_scale = []
                    y_scale = []
                    centers = {}
                    for id in ids.flatten():
                        x_scale.append( (corners[id][0][1][1] - corners[id][0][0][1]) / arucoWidth_mm )
                        x_scale.append( (corners[id][0][2][1] - corners[id][0][3][1]) / arucoWidth_mm )
                        y_scale.append( (corners[id][0][3][0] - corners[id][0][0][0]) / arucoHeight_mm )
                        y_scale.append( (corners[id][0][2][0] - corners[id][0][1][0]) / arucoHeight_mm )
    
                    for i, corner_set in enumerate(corners):
                        pts = corner_set[0]  # shape (4, 2)

                        # Center: average of the 4 corners
                        center_x = np.mean(pts[:, 1])
                        center_y = np.mean(pts[:, 0])
                        centers[ids[i][0]] = [center_x, center_y]

                    scale = [sum(x_scale)/len(x_scale), sum(y_scale)/len(y_scale)] 
                    self.distance_Y = (centers[0][1] - centers[1][1]) * (1 / scale[1])
                    self.distance_label.setText(f"{self.distance_Y:.3f}")

        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_qt_format.scaled(640, 480, Qt.KeepAspectRatio)

        if camera_id == 0:
            self.camera1_label.setPixmap(QPixmap.fromImage(p))
            self.lastFrames[0] = image
        elif camera_id == 1:
            self.camera2_label.setPixmap(QPixmap.fromImage(p))
            self.lastFrames[1] = image

    def toggle_aruco_detection(self):
        if not self.aruco_detection:
            self.aruco_detection = True
            self.toggle_aruco.setText("Terminar detección")
            self.terminal.append("Detección de arucos activada.")
            self.capture_deformation_btn.setEnabled(False)
        else:
            self.aruco_detection = False
            self.toggle_aruco.setText("Detectar Arucos")
            self.terminal.append("Detección de arucos desactivada.")
            if self.debug:
                self.capture_deformation_btn.setEnabled(True)
        # Verificar si todos los requisitos están listos para habilitar el botón de experimento
        self.check_experiment_requirements()

    def refresh_ports(self):
        self.port_combo.clear()
        ports = [port.device for port in serial.tools.list_ports.comports()]
        if ports:
            self.port_combo.addItems(ports)
        else:
            self.terminal.append("No se encontraron puertos seriales disponibles.")


    def toggle_connection(self):
        if not self.serial_connected:
            port = self.port_combo.currentText()
            baudrate = int(self.baudrate_combo.currentText())
            
            if not port:
                QMessageBox.warning(self, "Error", "No hay puertos disponibles.")
                return
                
            if self.serial_thread.connect_serial(port, baudrate):
                self.serial_thread.start()
            
        else:
            self.serial_thread.stop()
            self.terminal.append("Conexión serial cerrada.")
            self.serial_connected = False
            self.arduino_validated = False
            self.connect_btn.setText("Iniciar comunicación")
            self.port_combo.setEnabled(True)
            self.baudrate_combo.setEnabled(True)
            self.validate_btn.setEnabled(True)
            self.start_experiment_btn.setEnabled(False)


    def on_connection_status(self, status, message):
        self.terminal.append(message)
        self.serial_connected = status
        
        if status:
            self.connect_btn.setText("Cerrar comunicación")
            self.port_combo.setEnabled(False)
            self.baudrate_combo.setEnabled(False)
            
            # Verificar si todos los requisitos están listos para habilitar el botón de experimento
            self.check_experiment_requirements()
        else:
            self.connect_btn.setText("Iniciar comunicación")
            self.port_combo.setEnabled(True)
            self.baudrate_combo.setEnabled(True)
            self.start_experiment_btn.setEnabled(False)
    

    def on_data_received(self, data):
        self.terminal.append(f"RX: {data}")
        self.terminal.verticalScrollBar().setValue(self.terminal.verticalScrollBar().maximum())
        
        # Si recibimos "VALIDATED", habilitamos el botón de experimento
        if "VALIDATED" in data:
            self.arduino_validated = True
            self.terminal.append("Comunicación con Arduino validada correctamente.")
            # Verificar si todos los requisitos están listos para habilitar el botón de experimento
            self.check_experiment_requirements()
        if "TERMINATED" in data:
            self.experiment_finished = True
            self.terminal.append("Experimento terminado.")
            # Verificar si todos los requisitos están listos para habilitar el botón de experimento
            self.toggle_experiment()
    
    def validate_connection(self):
        if not self.serial_connected:
            QMessageBox.warning(self, "Error", "Primero debe establecer la conexión serial.")
            return
            
        # Enviar comando de validación
        self.serial_thread.write_data("VALIDATE\n")
        self.terminal.append("Validando conexión con Arduino...")

    def on_json_data_received(self, data):
        # Actualizar lecturas de sensores
        if "current_mA" in data:
            self.current_label.setText(f"{data['current_mA']:.3f}")
        if "relay_state" in data:
            self.relay_state = data['relay_state']  # Debe ser True o False
        if "force_N" in data:
            self.raw_force = data['force_N']
            if self.relay_state:
                calibrated_force = (self.raw_force - self.force_offset_relay) * self.force_scale_relay 
            else:
                calibrated_force = (self.raw_force - self.force_offset) * self.force_scale
            self.force_label.setText(f"{calibrated_force:.3f}")
        if "busVoltage_SMA_V" in data:
            self.voltage_sma_label.setText(f"{data['busVoltage_SMA_V']:.3f}")
        if "busVoltage_ref_V" in data:
            self.voltage_ref_label.setText(f"{data['busVoltage_ref_V']:.3f}")
            
        # Si estamos en experimento, guardar datos
        if self.experiment_running:
            self.save_experiment_data(data)

    def save_experiment_data(self, data):
        # Crear timestamp para este punto de datos
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Milisegundos
        
        # Guardar datos en CSV
        csv_path = os.path.join(self.data_folder, f"{self.current_timestamp}","data.csv")
        with open(csv_path, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                timestamp,
                data.get('current_mA', 0),
                (data.get('force_N', 0) - self.force_offset) * self.force_scale,  # Aplicar calibración
                data.get('busVoltage_SMA_V', 0),
                data.get('busVoltage_ref_V', 0),
                self.distance_Y - self.zero_deformation
            ])
            
        # Capturar frames de las cámaras
        for i in range(len(self.lastFrames)):
            frame = self.lastFrames[i]
            if frame is not None:
                frame_path = os.path.join(self.data_folder, f"{self.current_timestamp}",f"cam{i+1}", f"{timestamp}.jpg")
                cv2.imwrite(frame_path, frame)

    def clear_terminal(self):
        self.terminal.clear()

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta para guardar datos")
        if folder:
            self.data_folder = folder
            self.folder_edit.setText(folder)
            
            # Verificar si todos los requisitos están listos para habilitar el botón de experimento
            self.check_experiment_requirements()

    def toggle_experiment(self):
        if not self.experiment_running:
            # Iniciar experimento
            self.experiment_finished = False
            active_time = self.active_time_spin.value()
            rest_time = self.rest_time_spin.value()

            # Crear timestamp para identificar este experimento
            self.current_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            # Crear carpetas para las imágenes de las cámaras
            os.makedirs(os.path.join(self.data_folder, f"{self.current_timestamp}","cam1"), exist_ok=True)
            os.makedirs(os.path.join(self.data_folder, f"{self.current_timestamp}","cam2"), exist_ok=True)

            # Crear archivo CSV para los datos
            csv_path = os.path.join(self.data_folder, f"{self.current_timestamp}","data.csv")
            with open(csv_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'current_mA', 'force_N', 'busVoltage_SMA_V', 'busVoltage_ref_V','deflexion_mm'])
            
            # Enviar comando de inicio al Arduino
            command = f"START {active_time} {rest_time}\n"
            if self.serial_thread.write_data(command):
                self.terminal.append(f"Experimento iniciado - Tiempo activo: {active_time}ms, Tiempo reposo: {rest_time}ms")
                self.experiment_running = True
                self.start_experiment_btn.setText("Detener experimento")

                # Deshabilitar configuración durante el experimento
                self.active_time_spin.setEnabled(False)
                self.rest_time_spin.setEnabled(False)
                self.browse_btn.setEnabled(False)
            else:
                self.terminal.append("Error al iniciar el experimento")

        else:
            if  not self.experiment_finished:
            # Detener experimento
                if self.serial_thread.write_data("STOP\n"):
                    self.terminal.append("Experimento detenido")
                    self.experiment_finished = True

            self.experiment_running = False
            self.start_experiment_btn.setText("Iniciar experimento")
            
            # Habilitar configuración
            self.active_time_spin.setEnabled(True)
            self.rest_time_spin.setEnabled(True)
            self.browse_btn.setEnabled(True)

    def debug_sensores(self):
        if not self.serial_connected:
            QMessageBox.warning(self, "Error", "Primero debe establecer la conexión serial.")
            return
        else:
            if not self.debug:
                if self.serial_thread.write_data("DEBUG\n"):
                    self.terminal.append("Leyendo sensores para calibración...")
                    self.debug_sensor_btn.setText("Detener calibración")
                    self.debug = True
                    self.calibrate_force_combined_btn.setEnabled(True)
                    self.toggle_relay_btn.setEnabled(True)
                    if not self.aruco_detection:
                        self.capture_deformation_btn.setEnabled(True)
            else:
                # Enviar comando para detener lectura de sensores
                if self.serial_thread.write_data("DEBUGEND\n"):
                    self.terminal.append("Terminando calibración...")
                    self.debug_sensor_btn.setText("Leer Sensores")
                    self.debug = False 
                    self.calibrate_force_combined_btn.setEnabled(False)
                    self.toggle_relay_btn.setEnabled(False)
                    self.capture_deformation_btn.setEnabled(False)
                    if self.relay_active:
                        if self.serial_thread.write_data("RELAY_OFF\n"):
                            self.terminal.append("Desactivando relevador")
                            self.toggle_relay_btn.setText("Activar relevador")
                            self.relay_active = False
        # Verificar si todos los requisitos están listos para habilitar el botón de experimento
        self.check_experiment_requirements() 

    def show_force_calibration_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Opciones de calibración de fuerza")
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Selecciona tipo de calibración:"))
        option_combo = QComboBox()
        options = [
            "Capturar 0 N (Relevador OFF)",
            "Capturar peso conocido (Relevador OFF)",
            "Capturar 0 N (Relevador ON)",
            "Capturar peso conocido (Relevador ON)"
        ]
        option_combo.addItems(options)
        layout.addWidget(option_combo)

        known_force_input = QDoubleSpinBox()
        known_force_input.setRange(0.0, 10000.0)
        known_force_input.setDecimals(3)
        known_force_input.setSuffix(" N")
        known_force_input.setSingleStep(0.1)
        known_force_input.setVisible(False)
        layout.addWidget(QLabel("Valor conocido (N):"))
        layout.addWidget(known_force_input)

        # Mostrar el input solo si es calibración con peso
        def toggle_input_visibility(index):
            known_force_input.setVisible(index in [1, 3])
        option_combo.currentIndexChanged.connect(toggle_input_visibility)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            option = option_combo.currentIndex()
            raw = float(self.raw_force)

            try:
                if option == 0:
                    self.force_offset = raw
                    self.terminal.append(f"Offset 0 N (Rele OFF): {self.force_offset:.3f}")
                elif option == 1:
                    known = known_force_input.value()
                    if raw == self.force_offset:
                        raise ValueError("Offset igual a lectura actual")
                    self.force_scale = known / (raw - self.force_offset)
                    self.terminal.append(f"Escala (Rele OFF): {self.force_scale:.3f}")
                elif option == 2:
                    self.force_offset_relay = raw
                    self.terminal.append(f"Offset 0 N (Rele ON): {self.force_offset_relay:.3f}")
                elif option == 3:
                    known = known_force_input.value()
                    if raw == self.force_offset_relay:
                        raise ValueError("Offset igual a lectura actual (Rele ON)")
                    self.force_scale_relay = known / (raw - self.force_offset_relay)
                    self.terminal.append(f"Escala (Rele ON): {self.force_scale_relay:.3f}")
            except Exception as e:
                QMessageBox.critical(self, "Error de calibración", f"Error: {str(e)}")

    def toggle_relay(self):
        if not self.relay_active:
            if self.serial_thread.write_data("RELAY_ON\n"):
                self.terminal.append("Activando relevador")
                self.toggle_relay_btn.setText("Desactivar relevador")
                self.relay_active = True
        else:
            if self.serial_thread.write_data("RELAY_OFF\n"):
                self.terminal.append("Desactivando relevador")
                self.toggle_relay_btn.setText("Activar relevador")
                self.relay_active = False

    def capture_zero_deformation(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Milisegundos
        cwd = os.getcwd()
        try:
            frame = self.lastFrames[0]
            if frame is not None:
                frame_path = os.path.join(cwd,'Calibration', f"{timestamp}.jpg")
                cv2.imwrite(frame_path, frame)
                self.terminal.append("Imagen para calibración guardada correctamente")
                self.zero_deformation = self.distance_Y
            else:
                self.terminal.append("No se encontro imagen de la camara 1")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar imagen:\n{str(e)}")
            self.terminal.append(f"[ERROR] {str(e)}")    

    def check_experiment_requirements(self):
        # Verificar todos los requisitos para habilitar el botón de experimento
        valid_active_time = self.active_time_spin.value() > 0
        valid_rest_time = self.rest_time_spin.value() > 0
        valid_folder = bool(self.data_folder)
        
        if valid_active_time and valid_rest_time and valid_folder and self.serial_connected and not self.debug and self.arduino_validated and not self.aruco_detection:
            self.start_experiment_btn.setEnabled(True)
        else:
            self.start_experiment_btn.setEnabled(False)


    def create_calibration_directory(self):
        cwd = os.getcwd()
        os.makedirs(os.path.join(cwd,'Calibration'), exist_ok=True)
            
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Estilo más moderno
    window = SMACharacterizationApp()
    window.show()
    sys.exit(app.exec_())