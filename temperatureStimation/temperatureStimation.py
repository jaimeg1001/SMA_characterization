import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import pandas as pd
import numpy as np
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import re
import sys

class TemperatureAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Analizador de Temperatura RGB")
        self.root.geometry("1200x900")
        
        # Variables principales
        self.images_folder = ""
        self.data_csv_file = ""
        self.rgb_temp_csv_file = ""
        self.data_df = None
        self.rgb_data = None
        self.current_image_index = 0
        self.point_positions = [None, None, None]
        self.point_markers = []
        self.images_list = []
        self.temp_data = {}
        self.default_positions = None
        self.first_points_set = False
        self.deleted_images = set()  # Conjunto de índices de imágenes eliminadas
        
        # Variables para el control del canvas
        self.img = None
        self.fig = None
        self.ax = None
        self.canvas = None
        
        self._create_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_ui(self):
        """Crea toda la interfaz de usuario"""
        # Frame superior para botones de selección
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)
        
        buttons_config = [
            ("Seleccionar Carpeta de Imágenes", self._select_folder),
            ("Seleccionar data.csv", self._select_data_csv),
            ("Seleccionar CSV de RGB-Temperatura", self._select_rgb_temp_csv),
            ("Iniciar Análisis", self._start_analysis)
        ]
        
        for i, (text, command) in enumerate(buttons_config):
            ttk.Button(top_frame, text=text, command=command).grid(row=0, column=i, padx=5)
        
        # Frame central para mostrar la imagen
        self.image_frame = ttk.Frame(self.root, padding=10)
        self.image_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame inferior para navegación y controles
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.pack(fill=tk.X)
        
        # Botones de navegación
        nav_buttons = [
            ("⏮ Primera", self._go_to_first),
            ("◀ Anterior", self._go_to_previous),
            ("Siguiente ▶", self._go_to_next),
            ("Última ⏭", self._go_to_last),
            ("🗑 Eliminar Imagen", self._delete_current_image),
            ("💾 Guardar Datos", self._save_data)
        ]
        
        for i, (text, command) in enumerate(nav_buttons[:4]):
            ttk.Button(bottom_frame, text=text, command=command).grid(row=0, column=i, padx=5)
        
        self.image_label = ttk.Label(bottom_frame, text="Imagen: ")
        self.image_label.grid(row=0, column=4, padx=20)
        
        # Estado de imagen (normal/eliminada)
        self.status_label = ttk.Label(bottom_frame, text="", foreground="red")
        self.status_label.grid(row=0, column=5, padx=10)
        
        # Botones de eliminar y guardar
        ttk.Button(bottom_frame, text=nav_buttons[4][0], 
                  command=nav_buttons[4][1]).grid(row=0, column=6, padx=10)
        ttk.Button(bottom_frame, text=nav_buttons[5][0], 
                  command=nav_buttons[5][1]).grid(row=0, column=7, padx=10)
        
        # Sección de resultados
        results_frame = ttk.LabelFrame(self.root, text="Temperaturas", padding=10)
        results_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.temp_labels = []
        for i in range(3):
            label = ttk.Label(results_frame, text=f"Punto {i+1}: --")
            label.grid(row=0, column=i, padx=20)
            self.temp_labels.append(label)
    
    def _select_folder(self):
        """Selecciona la carpeta con imágenes"""
        folder = filedialog.askdirectory(title="Seleccionar carpeta de imágenes")
        if folder:
            self.images_folder = folder
            messagebox.showinfo("Información", f"Carpeta seleccionada: {folder}")
    
    def _select_data_csv(self):
        """Selecciona el archivo data.csv"""
        csv_file = filedialog.askopenfilename(
            title="Seleccionar archivo data.csv",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if csv_file:
            self.data_csv_file = csv_file
            try:
                self.data_df = pd.read_csv(csv_file)
                required_columns = ['timestamp', 'current_mA', 'force_N', 
                                   'busVoltage_SMA_V', 'busVoltage_ref_V', 'deflexion_mm']
                missing_columns = [col for col in required_columns if col not in self.data_df.columns]
                
                if missing_columns:
                    messagebox.showwarning("Advertencia", 
                        f"Faltan columnas: {', '.join(missing_columns)}")
                else:
                    messagebox.showinfo("Información", f"Archivo data.csv cargado: {csv_file}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar data.csv: {str(e)}")
    
    def _select_rgb_temp_csv(self):
        """Selecciona el archivo rgb_corrected_temperature_data.csv"""
        csv_file = filedialog.askopenfilename(
            title="Seleccionar archivo rgb_corrected_temperature_data.csv",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if csv_file:
            self.rgb_temp_csv_file = csv_file
            try:
                self.rgb_data = pd.read_csv(csv_file)
                print(f"Datos RGB cargados: {len(self.rgb_data)} entradas")
                
                if not all(col in self.rgb_data.columns for col in ['Temperature', 'R', 'G', 'B']):
                    messagebox.showerror("Error", "El CSV RGB no contiene las columnas necesarias")
                    self.rgb_data = None
                    return
                messagebox.showinfo("Información", f"Archivo RGB-Temperatura cargado: {csv_file}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar RGB-Temperatura: {str(e)}")
    
    def _start_analysis(self):
        """Inicia el análisis de imágenes"""
        if not all([self.images_folder, self.data_csv_file, self.rgb_temp_csv_file]):
            messagebox.showerror("Error", "Debe seleccionar carpeta de imágenes y ambos archivos CSV")
            return
        
        if self.data_df is None or self.rgb_data is None:
            messagebox.showerror("Error", "Error al cargar los archivos CSV")
            return
        
        try:
            self._match_images_to_timestamps()
            if not self.images_list:
                messagebox.showerror("Error", "No se encontraron imágenes correspondientes")
                return
            
            self.current_image_index = 0
            self.first_points_set = False
            self.deleted_images.clear()
            self._load_current_image()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar análisis: {str(e)}")
    
    def _match_images_to_timestamps(self):
        """Busca imágenes correspondientes a los timestamps"""
        self.images_list = []
        timestamps = self.data_df['timestamp'].astype(str).tolist()
        all_files = [f for f in os.listdir(self.images_folder) 
                    if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        for ts in timestamps:
            matched_file = self._find_matching_file(str(ts), all_files)
            if matched_file:
                self.images_list.append(matched_file)
    
    def _find_matching_file(self, timestamp, files):
        """Encuentra el archivo que coincide con el timestamp"""
        # Coincidencia exacta
        for file in files:
            if timestamp in file:
                return file
        
        # Coincidencia por números extraídos
        for file in files:
            numbers = re.findall(r'\d+', file)
            if timestamp in numbers:
                return file
        return None
    
    def _load_current_image(self):
        """Carga y muestra la imagen actual"""
        if not self.images_list or self.current_image_index >= len(self.images_list):
            return
        
        image_path = os.path.join(self.images_folder, self.images_list[self.current_image_index])
        timestamp = self.data_df['timestamp'].iloc[self.current_image_index]
        
        # Actualizar etiquetas
        self.image_label.config(text=f"Imagen: {self.images_list[self.current_image_index]} (TS: {timestamp})")
        
        # Mostrar estado de eliminación
        if self.current_image_index in self.deleted_images:
            self.status_label.config(text="ELIMINADA", foreground="red")
        else:
            self.status_label.config(text="", foreground="black")
        
        try:
            self._setup_image_canvas(image_path)
            self._restore_or_set_default_positions(timestamp)
            self._draw_points()
            self._calculate_temperatures()
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar imagen: {str(e)}")
    
    def _restore_or_set_default_positions(self, timestamp):
        """Restaura posiciones guardadas o establece posiciones por defecto"""
        if timestamp in self.temp_data:
            # Restaurar posiciones guardadas
            for i, point_data in enumerate(self.temp_data[timestamp]):
                if point_data is not None:
                    self.point_positions[i] = (point_data['x'], point_data['y'])
        elif self.default_positions:
            # Usar posiciones por defecto
            self.point_positions = self.default_positions.copy()
        else:
            # Resetear posiciones
            self.point_positions = [None, None, None]
    
    def _setup_image_canvas(self, image_path):
        """Configura el canvas para mostrar la imagen"""
        # Limpiar canvas anterior
        for widget in self.image_frame.winfo_children():
            widget.destroy()
        
        self.img = Image.open(image_path)
        
        plt.close('all')
        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        self.ax.imshow(self.img)
        self.ax.set_title("Haga clic para seleccionar 3 puntos")
        self.ax.axis('off')
        
        canvas_widget = FigureCanvasTkAgg(self.fig, master=self.image_frame)
        self.canvas = canvas_widget.get_tk_widget()
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
    
    def _on_click(self, event):
        """Maneja clics en la imagen para seleccionar puntos"""
        if event.xdata is None or event.ydata is None:
            return
        
        x, y = int(event.xdata), int(event.ydata)
        
        # Encontrar punto más cercano o crear nuevo
        closest_idx = self._find_closest_point(x, y)
        
        if closest_idx >= 0:
            self.point_positions[closest_idx] = (x, y)
        else:
            # Crear punto nuevo si hay espacio
            for i, pos in enumerate(self.point_positions):
                if pos is None:
                    self.point_positions[i] = (x, y)
                    break
        
        # Establecer posiciones por defecto en primera configuración completa
        if (all(pos is not None for pos in self.point_positions) and 
            not self.first_points_set):
            self.default_positions = self.point_positions.copy()
            self.first_points_set = True
            messagebox.showinfo("Información", 
                "Posiciones iniciales establecidas como referencia por defecto.")
        
        self._draw_points()
        self._calculate_temperatures()
    
    def _find_closest_point(self, x, y, threshold=20):
        """Encuentra el punto más cercano dentro del umbral"""
        closest_idx = -1
        min_distance = float('inf')
        
        for i, pos in enumerate(self.point_positions):
            if pos is not None:
                dist = ((pos[0] - x) ** 2 + (pos[1] - y) ** 2) ** 0.5
                if dist < threshold and dist < min_distance:
                    closest_idx = i
                    min_distance = dist
        
        return closest_idx
    
    def _draw_points(self):
        """Dibuja los puntos en la imagen"""
        # Limpiar marcadores anteriores
        for marker in self.point_markers:
            if marker:
                marker.remove()
        self.point_markers = []
        
        colors = ['red', 'green', 'magenta']
        
        for i, pos in enumerate(self.point_positions):
            if pos is not None:
                x, y = pos
                marker = self.ax.plot(x, y, 'o', color=colors[i], markersize=10, 
                                     label=f"Punto {i+1}")[0]
                self.point_markers.append(marker)
        
        if any(pos is not None for pos in self.point_positions):
            self.ax.legend()
        
        self.fig.canvas.draw()
    
    def _calculate_temperatures(self):
        """Calcula temperaturas para los puntos seleccionados"""
        if not hasattr(self, 'img') or self.img is None:
            return
        
        timestamp = self.data_df['timestamp'].iloc[self.current_image_index]
        
        if timestamp not in self.temp_data:
            self.temp_data[timestamp] = [None, None, None]
        
        # Resetear etiquetas
        for i in range(3):
            self.temp_labels[i].config(text=f"Punto {i+1}: --")
        
        # Calcular para cada punto
        for i, pos in enumerate(self.point_positions):
            if pos is not None:
                try:
                    x, y = pos
                    r, g, b = self.img.getpixel((x, y))[:3]
                    temp = self._infer_temperature_fuzzy(r, g, b)
                    
                    self.temp_data[timestamp][i] = {
                        'x': x, 'y': y, 'r': r, 'g': g, 'b': b, 'temperature': temp
                    }
                    
                    self.temp_labels[i].config(
                        text=f"Punto {i+1}: {temp:.2f} °C (R={r}, G={g}, B={b})")
                    
                except Exception as e:
                    print(f"Error al procesar punto {i+1}: {str(e)}")
        
        self.root.update_idletasks()
    
    def _infer_temperature_fuzzy(self, r, g, b, k=10):
        """Infiere temperatura usando enfoque fuzzy"""
        if self.rgb_data is None:
            return 0
        
        temps = self.rgb_data['Temperature'].values
        rgb_data = self.rgb_data[['R', 'G', 'B']].values
        
        input_rgb = np.array([r, g, b])
        distances = np.linalg.norm(rgb_data - input_rgb, axis=1)
        weights = np.exp(-k * distances**2)
        
        if np.sum(weights) < 1e-8:
            return temps[np.argmin(distances)]
        
        weights /= np.sum(weights)
        return np.dot(weights, temps)
    
    def _delete_current_image(self):
        """Elimina/restaura la imagen actual del análisis"""
        if not self.images_list:
            return
        
        if self.current_image_index in self.deleted_images:
            # Restaurar imagen
            self.deleted_images.remove(self.current_image_index)
            self.status_label.config(text="", foreground="black")
            messagebox.showinfo("Información", "Imagen restaurada al análisis")
        else:
            # Eliminar imagen
            if messagebox.askyesno("Confirmar", 
                "¿Está seguro de eliminar esta imagen del análisis?\n"
                "No se incluirá en el CSV final."):
                self.deleted_images.add(self.current_image_index)
                self.status_label.config(text="ELIMINADA", foreground="red")
                
                # Eliminar datos de temperatura asociados
                timestamp = self.data_df['timestamp'].iloc[self.current_image_index]
                if timestamp in self.temp_data:
                    del self.temp_data[timestamp]
                
                # Limpiar visualización
                for label in self.temp_labels:
                    label.config(text=label.cget("text").split(":")[0] + ": --")
    
    # Métodos de navegación simplificados
    def _go_to_first(self):
        if self.images_list:
            self.current_image_index = 0
            self._load_current_image()
    
    def _go_to_previous(self):
        if self.images_list and self.current_image_index > 0:
            self.current_image_index -= 1
            self._load_current_image()
    
    def _go_to_next(self):
        if self.images_list and self.current_image_index < len(self.images_list) - 1:
            self.current_image_index += 1
            self._load_current_image()
    
    def _go_to_last(self):
        if self.images_list:
            self.current_image_index = len(self.images_list) - 1
            self._load_current_image()
    
    def _save_data(self):
        """Guarda los datos de temperatura, procesando automáticamente imágenes válidas"""
        if self.data_df is None:
            messagebox.showwarning("Advertencia", "No hay datos para guardar")
            return
        
        if not self._validate_save_conditions():
            return
        
        try:
            self._prepare_dataframe_columns()
            current_index = self.current_image_index
            
            # Procesar imágenes no visitadas (excluyendo eliminadas)
            unprocessed = self._get_unprocessed_images()
            
            if unprocessed and self.default_positions:
                if messagebox.askyesno("Procesar imágenes", 
                    f"¿Procesar {len(unprocessed)} imágenes automáticamente?"):
                    self._process_images_batch(unprocessed)
            
            self._update_dataframe_with_temperatures()
            self._save_filtered_dataframe()
            
            messagebox.showinfo("Éxito", "Datos guardados correctamente")
            self.current_image_index = current_index
            self._load_current_image()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {str(e)}")
    
    def _validate_save_conditions(self):
        """Valida condiciones para guardar"""
        if not self.default_positions or not all(pos is not None for pos in self.default_positions):
            if not self.temp_data:
                messagebox.showwarning("Advertencia", "No hay puntos definidos")
                return False
            else:
                # Usar primera entrada como referencia
                first_timestamp = next(iter(self.temp_data))
                if all(point is not None for point in self.temp_data[first_timestamp]):
                    self.default_positions = [(point['x'], point['y']) 
                                            for point in self.temp_data[first_timestamp]]
        return True
    
    def _prepare_dataframe_columns(self):
        """Prepara columnas en el DataFrame"""
        for i in range(3):
            for col_type in ['temp', 'x', 'y']:
                col_name = f'{col_type}_point{i+1}'
                if col_name not in self.data_df.columns:
                    self.data_df[col_name] = None
    
    def _get_unprocessed_images(self):
        """Obtiene lista de imágenes no procesadas y no eliminadas"""
        unprocessed = []
        for i, timestamp in enumerate(self.data_df['timestamp']):
            if (timestamp not in self.temp_data and 
                i < len(self.images_list) and 
                i not in self.deleted_images):
                unprocessed.append((i, timestamp))
        return unprocessed
    
    def _process_images_batch(self, unprocessed_list):
        """Procesa un lote de imágenes automáticamente"""
        progress_window = self._create_progress_window(len(unprocessed_list))
        
        for count, (idx, ts) in enumerate(unprocessed_list):
            image_path = os.path.join(self.images_folder, self.images_list[idx])
            try:
                img = Image.open(image_path)
                self.temp_data[ts] = [None, None, None]
                
                for i, pos in enumerate(self.default_positions):
                    if pos and 0 <= pos[0] < img.width and 0 <= pos[1] < img.height:
                        x, y = pos
                        r, g, b = img.getpixel((x, y))[:3]
                        temp = self._infer_temperature_fuzzy(r, g, b)
                        
                        self.temp_data[ts][i] = {
                            'x': x, 'y': y, 'r': r, 'g': g, 'b': b, 'temperature': temp
                        }
                
                self._update_progress(progress_window, count + 1, len(unprocessed_list))
                
            except Exception as e:
                print(f"Error procesando {image_path}: {str(e)}")
        
        progress_window.destroy()
    
    def _create_progress_window(self, total):
        """Crea ventana de progreso"""
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Procesando imágenes")
        progress_window.geometry("300x100")
        
        progress_window.label = ttk.Label(progress_window, text="Procesando imágenes...")
        progress_window.label.pack(pady=10)
        
        progress_window.bar = ttk.Progressbar(progress_window, orient="horizontal", 
                                            length=250, mode="determinate", maximum=total)
        progress_window.bar.pack(pady=10)
        
        progress_window.update()
        return progress_window
    
    def _update_progress(self, window, current, total):
        """Actualiza la barra de progreso"""
        window.bar["value"] = current
        window.label.config(text=f"Procesando imagen {current} de {total}")
        window.update()
    
    def _update_dataframe_with_temperatures(self):
        """Actualiza el DataFrame con datos de temperatura"""
        for timestamp, points in self.temp_data.items():
            idx = self.data_df[self.data_df['timestamp'] == timestamp].index
            if len(idx) == 0:
                continue
            
            for i, point_data in enumerate(points):
                if point_data is not None:
                    self.data_df.loc[idx, f'temp_point{i+1}'] = point_data['temperature']
                    self.data_df.loc[idx, f'x_point{i+1}'] = point_data['x']
                    self.data_df.loc[idx, f'y_point{i+1}'] = point_data['y']
    
    def _save_filtered_dataframe(self):
        """Guarda el DataFrame excluyendo filas eliminadas"""
        # Crear DataFrame filtrado (excluir imágenes eliminadas)
        valid_indices = [i for i in range(len(self.data_df)) if i not in self.deleted_images]
        filtered_df = self.data_df.iloc[valid_indices].copy()
        
        # Guardar DataFrame filtrado
        filtered_df.to_csv(self.data_csv_file, index=False)
        
        if self.deleted_images:
            print(f"Se excluyeron {len(self.deleted_images)} imágenes del archivo final")
    
    def _on_closing(self):
        """Maneja el cierre de la ventana"""
        try:
            plt.close('all')
            if self.temp_data and messagebox.askyesno("Guardar", 
                "¿Desea guardar los datos antes de salir?"):
                self._save_data()
            self.root.destroy()
        except Exception as e:
            print(f"Error al cerrar: {str(e)}")
            self.root.destroy()
            sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = TemperatureAnalyzer(root)
    root.mainloop()