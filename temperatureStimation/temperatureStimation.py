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
        self.root.geometry("1000x800")
        
        # Variables principales
        self.images_folder = ""
        self.data_csv_file = ""  # CSV de datos donde se almacenarán resultados
        self.rgb_temp_csv_file = ""  # CSV con datos RGB para inferencia
        self.data_df = None  # DataFrame para data.csv
        self.rgb_data = None  # DataFrame para rgb_corrected_temperature_data.csv
        self.current_image_index = 0
        self.point_positions = [None, None, None]  # Almacena las posiciones (x, y) de los 3 puntos
        self.point_markers = []
        self.images_list = []
        self.temp_data = {}  # Almacena datos temporales de temperatura
        self.default_positions = None  # Almacenará las posiciones por defecto
        self.first_points_set = False  # Bandera para saber si los primeros puntos ya se han establecido
        
        # Variables para el control del canvas
        self.img = None
        self.fig = None
        self.ax = None
        self.canvas = None
        
        # Crear la estructura básica de la UI
        self.create_ui_structure()
        self._create_ui_controls()
        
        # Configurar manejador para cierre de ventana
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def create_ui_structure(self):
        """Crea la estructura básica de la interfaz de usuario"""
        # Frame superior para botones de selección
        self.top_frame = ttk.Frame(self.root, padding=10)
        self.top_frame.pack(fill=tk.X)
        
        # Frame central para mostrar la imagen
        self.image_frame = ttk.Frame(self.root, padding=10)
        self.image_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame inferior para navegación y resultados
        self.bottom_frame = ttk.Frame(self.root, padding=10)
        self.bottom_frame.pack(fill=tk.X)
        
        # Sección de resultados
        self.results_frame = ttk.LabelFrame(self.root, text="Temperaturas", padding=10)
        self.results_frame.pack(fill=tk.X, padx=10, pady=5)
    
    def _create_ui_controls(self):
        """Crea los controles de la interfaz de usuario"""
        # Botones de selección en el frame superior
        ttk.Button(self.top_frame, text="Seleccionar Carpeta de Imágenes", 
                  command=self._select_folder).grid(row=0, column=0, padx=5)
        ttk.Button(self.top_frame, text="Seleccionar data.csv", 
                  command=self._select_data_csv).grid(row=0, column=1, padx=5)
        ttk.Button(self.top_frame, text="Seleccionar CSV de RGB-Temperatura", 
                  command=self._select_rgb_temp_csv).grid(row=0, column=2, padx=5)
        ttk.Button(self.top_frame, text="Iniciar Análisis", 
                  command=self._start_analysis).grid(row=0, column=3, padx=5)
        
        # Botones de navegación en el frame inferior
        ttk.Button(self.bottom_frame, text="⏮ Primera", 
                  command=self._go_to_first).grid(row=0, column=0, padx=5)
        ttk.Button(self.bottom_frame, text="◀ Anterior", 
                  command=self._go_to_previous).grid(row=0, column=1, padx=5)
        
        self.image_label = ttk.Label(self.bottom_frame, text="Imagen: ")
        self.image_label.grid(row=0, column=2, padx=20)
        
        ttk.Button(self.bottom_frame, text="Siguiente ▶", 
                  command=self._go_to_next).grid(row=0, column=3, padx=5)
        ttk.Button(self.bottom_frame, text="Última ⏭", 
                  command=self._go_to_last).grid(row=0, column=4, padx=5)
        
        # Botón para guardar datos
        ttk.Button(self.bottom_frame, text="Guardar Datos", 
                  command=self._save_data).grid(row=0, column=5, padx=20)
        
        # Etiquetas para temperaturas
        self.temp_labels = []
        for i in range(3):
            label = ttk.Label(self.results_frame, text=f"Punto {i+1}: --")
            label.grid(row=0, column=i, padx=20)
            self.temp_labels.append(label)
    
    def _select_folder(self):
        """Permite al usuario seleccionar la carpeta con imágenes"""
        folder = filedialog.askdirectory(title="Seleccionar carpeta de imágenes")
        if folder:
            self.images_folder = folder
            messagebox.showinfo("Información", f"Carpeta seleccionada: {folder}")
    
    def _select_data_csv(self):
        """Permite al usuario seleccionar el archivo data.csv"""
        csv_file = filedialog.askopenfilename(
            title="Seleccionar archivo data.csv",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if csv_file:
            self.data_csv_file = csv_file
            try:
                # Verificar que el CSV tenga la estructura esperada
                self.data_df = pd.read_csv(csv_file)
                required_columns = ['timestamp', 'current_mA', 'force_N', 
                                   'busVoltage_SMA_V', 'busVoltage_ref_V', 'deflexion_mm']
                missing_columns = [col for col in required_columns if col not in self.data_df.columns]
                
                if missing_columns:
                    messagebox.showwarning(
                        "Advertencia", 
                        f"El archivo CSV no contiene todas las columnas esperadas. Faltan: {', '.join(missing_columns)}"
                    )
                else:
                    messagebox.showinfo("Información", f"Archivo data.csv cargado: {csv_file}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar el archivo data.csv: {str(e)}")
    
    def _select_rgb_temp_csv(self):
        """Permite al usuario seleccionar el archivo rgb_corrected_temperature_data.csv"""
        csv_file = filedialog.askopenfilename(
            title="Seleccionar archivo rgb_corrected_temperature_data.csv",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if csv_file:
            self.rgb_temp_csv_file = csv_file
            try:
                # Cargar datos RGB para la inferencia de temperatura
                self.rgb_data = pd.read_csv(csv_file)
                print(f"Datos RGB cargados: {len(self.rgb_data)} entradas")
                print(f"Columnas: {self.rgb_data.columns.tolist()}")
                print(f"Primeras 5 filas:\n{self.rgb_data.head()}")
                
                if not all(col in self.rgb_data.columns for col in ['Temperature', 'R', 'G', 'B']):
                    messagebox.showerror("Error", "El CSV RGB no contiene las columnas necesarias (Temperature, R, G, B)")
                    self.rgb_data = None
                    return
                messagebox.showinfo("Información", f"Archivo RGB-Temperatura cargado: {csv_file}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar el archivo RGB-Temperatura: {str(e)}")
                import traceback
                traceback.print_exc()
    
    def _start_analysis(self):
        """Inicia el análisis de imágenes cargando la primera imagen"""
        if not self.images_folder or not self.data_csv_file or not self.rgb_temp_csv_file:
            messagebox.showerror("Error", "Debe seleccionar una carpeta de imágenes y los dos archivos CSV")
            return
        
        try:
            # Comprobar que tenemos los datos necesarios
            if self.data_df is None or self.rgb_data is None:
                messagebox.showerror("Error", "Error al cargar los archivos CSV necesarios")
                return
            
            if 'timestamp' not in self.data_df.columns:
                messagebox.showerror("Error", "El archivo data.csv no contiene la columna 'timestamp'")
                return
            
            # Buscar las imágenes correspondientes a los timestamps
            self.images_list = []
            timestamps = self.data_df['timestamp'].astype(str).tolist()
            
            # Listar todos los archivos de imagen en la carpeta
            all_files = [f for f in os.listdir(self.images_folder) 
                       if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            # Mapear timestamps a imágenes usando coincidencia parcial
            for ts in timestamps:
                ts_str = str(ts)
                matched_file = None
                
                # Buscar coincidencia exacta primero
                for file in all_files:
                    if ts_str in file:
                        matched_file = file
                        break
                
                # Si no hay coincidencia exacta, usar coincidencia parcial
                if not matched_file:
                    for file in all_files:
                        numbers = re.findall(r'\d+', file)
                        for num in numbers:
                            if num == ts_str:
                                matched_file = file
                                break
                        if matched_file:
                            break
                
                if matched_file:
                    self.images_list.append(matched_file)
            
            if not self.images_list:
                messagebox.showerror("Error", "No se encontraron imágenes correspondientes a los timestamps")
                return
            
            # Iniciar con la primera imagen
            self.current_image_index = 0
            self.first_points_set = False  # Reiniciar la bandera al iniciar el análisis
            self._load_current_image()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar el análisis: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _load_current_image(self):
        """Carga y muestra la imagen actual"""
        if not self.images_list or self.current_image_index >= len(self.images_list):
            return
        
        image_path = os.path.join(self.images_folder, self.images_list[self.current_image_index])
        timestamp = self.data_df['timestamp'].iloc[self.current_image_index]
        
        # Actualizar etiqueta de imagen
        self.image_label.config(text=f"Imagen: {self.images_list[self.current_image_index]} (TS: {timestamp})")
        
        try:
            # Cargar la imagen y preparar el canvas
            self._setup_image_canvas(image_path)
            
            # Verificar si ya tenemos posiciones de punto guardadas para esta imagen
            if timestamp in self.temp_data:
                # Restaurar posiciones guardadas para esta imagen específica
                for i, point_data in enumerate(self.temp_data[timestamp]):
                    if point_data is not None:
                        self.point_positions[i] = (point_data['x'], point_data['y'])
            else:
                # Si no hay datos para esta imagen y ya se han establecido los primeros puntos,
                # usar los puntos por defecto (pero solo si están definidos)
                if self.default_positions:
                    self.point_positions = self.default_positions.copy()
            
            # Mostrar puntos existentes
            self._draw_points()
            
            # Calcular temperaturas cada vez que se carga una imagen
            self._calculate_temperatures()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar la imagen: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _setup_image_canvas(self, image_path):
        """Configura el canvas para mostrar la imagen y capturar clics"""
        # Limpiar el canvas anterior
        for widget in self.image_frame.winfo_children():
            widget.destroy()
        
        # Cargar la imagen
        self.img = Image.open(image_path)
        
        # Crear una figura de matplotlib y mostrarla en Tkinter
        plt.close('all')  # Cerrar todas las figuras abiertas
        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        self.ax.imshow(self.img)
        self.ax.set_title("Haga clic para seleccionar 3 puntos")
        self.ax.axis('off')  # Ocultar ejes
        
        # Crear el canvas de matplotlib en Tkinter
        canvas_widget = FigureCanvasTkAgg(self.fig, master=self.image_frame)
        self.canvas = canvas_widget.get_tk_widget()
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Conectar el evento de clic
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
    
    def _on_click(self, event):
        """Maneja los clics en la imagen para seleccionar puntos"""
        if event.xdata is None or event.ydata is None:
            return
        
        x, y = int(event.xdata), int(event.ydata)
        timestamp = self.data_df['timestamp'].iloc[self.current_image_index]
        
        # Encontrar el punto más cercano si alguno está lo suficientemente cerca
        closest_point_idx = -1
        min_distance = float('inf')
        
        for i, pos in enumerate(self.point_positions):
            if pos is not None:
                dist = ((pos[0] - x) ** 2 + (pos[1] - y) ** 2) ** 0.5
                if dist < 20 and dist < min_distance:  # Umbral de distancia para selección
                    closest_point_idx = i
                    min_distance = dist
        
        # Si hay un punto cercano, moverlo
        if closest_point_idx >= 0:
            self.point_positions[closest_point_idx] = (x, y)
        else:
            # Si no hay ningún punto cercano, crear uno nuevo si hay espacio
            for i, pos in enumerate(self.point_positions):
                if pos is None:
                    self.point_positions[i] = (x, y)
                    break
        
        # Si todos los puntos están colocados y es la primera vez
        if all(pos is not None for pos in self.point_positions) and not self.first_points_set:
            # Guardar como posiciones por defecto para futuras imágenes
            self.default_positions = self.point_positions.copy()
            self.first_points_set = True
            messagebox.showinfo("Información", "Posiciones iniciales establecidas. Estos puntos serán la referencia por defecto para las siguientes imágenes.")
        
        # Redibuja todos los puntos
        self._draw_points()
        
        # Calcular temperaturas
        self._calculate_temperatures()
    
    def _draw_points(self):
        """Dibuja los puntos en la imagen"""
        # Limpiar marcadores anteriores
        for marker in self.point_markers:
            if marker:
                marker.remove()
        self.point_markers = []
        
        # Colores para cada punto
        colors = ['red', 'green', 'magenta']
        
        # Dibujar nuevos marcadores
        for i, pos in enumerate(self.point_positions):
            if pos is not None:
                x, y = pos
                marker = self.ax.plot(x, y, 'o', color=colors[i], markersize=10, 
                                     label=f"Punto {i+1}")[0]
                self.point_markers.append(marker)
        
        # Actualizar leyenda y canvas
        if any(pos is not None for pos in self.point_positions):
            self.ax.legend()
        
        self.fig.canvas.draw()
    
    def _calculate_temperatures(self):
        """Calcula las temperaturas para los puntos seleccionados"""
        if not hasattr(self, 'img') or self.img is None:
            return
        
        timestamp = self.data_df['timestamp'].iloc[self.current_image_index]
        
        # Inicializar datos para este timestamp si no existen
        if timestamp not in self.temp_data:
            self.temp_data[timestamp] = [None, None, None]
        
        # Restablecer etiquetas primero
        for i in range(3):
            self.temp_labels[i].config(text=f"Punto {i+1}: --")
        
        # Calcular temperatura para cada punto
        for i, pos in enumerate(self.point_positions):
            if pos is not None:
                x, y = pos
                # Obtener valores RGB del píxel
                try:
                    r, g, b = self.img.getpixel((x, y))[:3]
                    
                    # Añadir mensaje de depuración
                    print(f"Punto {i+1} en ({x},{y}): RGB = ({r},{g},{b})")
                    
                    # Inferir temperatura usando la función del archivo original
                    temp = self._infer_temperature_fuzzy(r, g, b)
                    print(f"Temperatura inferida: {temp:.2f} °C")
                    
                    # Guardar el resultado y actualizar etiqueta
                    self.temp_data[timestamp][i] = {
                        'x': x, 
                        'y': y, 
                        'r': r, 
                        'g': g, 
                        'b': b, 
                        'temperature': temp
                    }
                    
                    # Actualizar la etiqueta con el nuevo texto
                    new_text = f"Punto {i+1}: {temp:.2f} °C (R={r}, G={g}, B={b})"
                    self.temp_labels[i].config(text=new_text)
                    
                except Exception as e:
                    print(f"Error al obtener el color del píxel ({x},{y}): {str(e)}")
                    import traceback
                    traceback.print_exc()
        
        # Actualizar ventana principal
        self.root.update_idletasks()
    
    def _infer_temperature_fuzzy(self, r, g, b, k=10):
        """Infiere la temperatura basada en valores RGB usando el enfoque fuzzy"""
        if self.rgb_data is None:
            return 0
        
        temps = self.rgb_data['Temperature'].values
        rgb_data = self.rgb_data[['R', 'G', 'B']].values
        
        input_rgb = np.array([r, g, b])
        distances = np.linalg.norm(rgb_data - input_rgb, axis=1)
        
        # Calcular pesos Gaussianos
        weights = np.exp(-k * distances**2)
        
        if np.sum(weights) < 1e-8:
            # Si todos los pesos son muy pequeños, usar el vecino más cercano
            nearest_idx = np.argmin(distances)
            return temps[nearest_idx]
        
        # Normalizar pesos de forma segura
        weights /= np.sum(weights)
        estimated_temp = np.dot(weights, temps)
        return estimated_temp
    
    def _go_to_first(self):
        """Va a la primera imagen"""
        if self.images_list:
            self.current_image_index = 0
            self._load_current_image()
    
    def _go_to_previous(self):
        """Va a la imagen anterior"""
        if self.images_list and self.current_image_index > 0:
            self.current_image_index -= 1
            self._load_current_image()
    
    def _go_to_next(self):
        """Va a la siguiente imagen"""
        if self.images_list and self.current_image_index < len(self.images_list) - 1:
            self.current_image_index += 1
            self._load_current_image()
    
    def _go_to_last(self):
        """Va a la última imagen"""
        if self.images_list:
            self.current_image_index = len(self.images_list) - 1
            self._load_current_image()
    
    def _save_data(self):
        """Guarda los datos de temperatura en el CSV de datos, procesando automáticamente todas las imágenes"""
        if self.data_df is None:
            messagebox.showwarning("Advertencia", "No hay datos para guardar")
            return
        
        # Verificar que tenemos posiciones por defecto para procesar todas las imágenes
        if not self.default_positions or not all(pos is not None for pos in self.default_positions):
            if not self.temp_data:  # Si no hay datos guardados para ninguna imagen
                messagebox.showwarning("Advertencia", "No hay puntos definidos para procesar las imágenes")
                return
            else:
                # Usar la primera entrada de temp_data para establecer posiciones por defecto
                first_timestamp = next(iter(self.temp_data))
                if all(point is not None for point in self.temp_data[first_timestamp]):
                    self.default_positions = [(point['x'], point['y']) for point in self.temp_data[first_timestamp]]
        
        try:
            # Preparar columnas para los 3 puntos si no existen
            for i in range(3):
                if f'temp_point{i+1}' not in self.data_df.columns:
                    self.data_df[f'temp_point{i+1}'] = None
                if f'x_point{i+1}' not in self.data_df.columns:
                    self.data_df[f'x_point{i+1}'] = None
                if f'y_point{i+1}' not in self.data_df.columns:
                    self.data_df[f'y_point{i+1}'] = None
            
            # Guardar el índice actual para restaurarlo después
            current_index = self.current_image_index
            
            # Procesar todas las imágenes que no han sido visitadas
            unprocessed_timestamps = []
            for i, timestamp in enumerate(self.data_df['timestamp']):
                if timestamp not in self.temp_data and i < len(self.images_list):
                    unprocessed_timestamps.append((i, timestamp))
            
            # Si hay imágenes sin procesar y tenemos posiciones por defecto
            if unprocessed_timestamps and self.default_positions:
                # Preguntar al usuario si desea procesar todas las imágenes pendientes
                if messagebox.askyesno("Procesar imágenes", 
                                    f"Hay {len(unprocessed_timestamps)} imágenes sin procesar. ¿Desea procesarlas automáticamente usando las posiciones por defecto?"):
                    # Mostrar barra de progreso
                    progress_window = tk.Toplevel(self.root)
                    progress_window.title("Procesando imágenes")
                    progress_window.geometry("300x100")
                    
                    progress_label = ttk.Label(progress_window, text="Procesando imágenes...")
                    progress_label.pack(pady=10)
                    
                    progress_bar = ttk.Progressbar(progress_window, orient="horizontal", 
                                                length=250, mode="determinate")
                    progress_bar.pack(pady=10)
                    progress_bar["maximum"] = len(unprocessed_timestamps)
                    
                    progress_window.update()
                    
                    # Procesar cada imagen pendiente
                    for count, (idx, ts) in enumerate(unprocessed_timestamps):
                        # Cargar la imagen
                        image_path = os.path.join(self.images_folder, self.images_list[idx])
                        try:
                            img = Image.open(image_path)
                            
                            # Inicializar datos para este timestamp
                            self.temp_data[ts] = [None, None, None]
                            
                            # Para cada punto, calcular temperatura usando la posición por defecto
                            for i, pos in enumerate(self.default_positions):
                                if pos is not None:
                                    x, y = pos
                                    # Verificar que las coordenadas estén dentro de los límites de la imagen
                                    if 0 <= x < img.width and 0 <= y < img.height:
                                        # Obtener valores RGB del píxel
                                        r, g, b = img.getpixel((x, y))[:3]
                                        # Inferir temperatura
                                        temp = self._infer_temperature_fuzzy(r, g, b)
                                        # Guardar datos
                                        self.temp_data[ts][i] = {
                                            'x': x,
                                            'y': y,
                                            'r': r,
                                            'g': g,
                                            'b': b,
                                            'temperature': temp
                                        }
                            
                            # Actualizar barra de progreso
                            progress_bar["value"] = count + 1
                            progress_label.config(text=f"Procesando imagen {count + 1} de {len(unprocessed_timestamps)}")
                            progress_window.update()
                            
                        except Exception as e:
                            print(f"Error al procesar la imagen {image_path}: {str(e)}")
                    
                    # Cerrar ventana de progreso
                    progress_window.destroy()
            
            # Actualizar el DataFrame con todos los datos recopilados
            for timestamp, points in self.temp_data.items():
                idx = self.data_df[self.data_df['timestamp'] == timestamp].index
                if len(idx) == 0:
                    continue
                
                for i, point_data in enumerate(points):
                    if point_data is not None:
                        self.data_df.loc[idx, f'temp_point{i+1}'] = point_data['temperature']
                        self.data_df.loc[idx, f'x_point{i+1}'] = point_data['x']
                        self.data_df.loc[idx, f'y_point{i+1}'] = point_data['y']
            
            # Guardar el DataFrame actualizado
            self.data_df.to_csv(self.data_csv_file, index=False)
            messagebox.showinfo("Éxito", "Datos guardados correctamente en data.csv")
            
            # Restaurar el índice de imagen original
            self.current_image_index = current_index
            self._load_current_image()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar los datos: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _on_closing(self):
        """Maneja el evento de cierre de la ventana"""
        try:
            # Cerrar todas las figuras de matplotlib
            plt.close('all')
            
            # Preguntar si desea guardar antes de salir
            if self.temp_data and messagebox.askyesno("Guardar", "¿Desea guardar los datos antes de salir?"):
                self._save_data()
            
            # Destruir la ventana principal
            self.root.destroy()
            
        except Exception as e:
            print(f"Error al cerrar la aplicación: {str(e)}")
            # Asegurar que la aplicación se cierre incluso si hay un error
            self.root.destroy()
            sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = TemperatureAnalyzer(root)
    root.mainloop()