import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Función para cargar y graficar datos
def cargar_csv():
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if not file_path:
        return

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        messagebox.showerror("Error al leer CSV", f"No se pudo leer el archivo:\n{str(e)}")
        return

    columnas_necesarias = ['timestamp', 'temp_point1', 'temp_point2', 'temp_point3']
    faltantes = [col for col in columnas_necesarias if col not in df.columns]

    if faltantes:
        messagebox.showwarning("Columnas faltantes", f"Las siguientes columnas no se encuentran en el archivo:\n{', '.join(faltantes)}")
        return

    # Limpiar el frame de la gráfica
    for widget in frame_grafica.winfo_children():
        widget.destroy()

    # Crear la figura
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(df['timestamp'], df['temp_point1'], label='Temperatura Punto 1', color='r')
    ax.plot(df['timestamp'], df['temp_point2'], label='Temperatura Punto 2', color='g')
    ax.plot(df['timestamp'], df['temp_point3'], label='Temperatura Punto 3', color='b')
    ax.set_title('Evolución de Temperatura en Función del Tiempo')
    ax.set_xlabel('Tiempo [s]')
    ax.set_ylabel('Temperatura [°C]')
    ax.legend()
    ax.grid(True)
    fig.tight_layout()

    # Mostrar en Tkinter
    canvas = FigureCanvasTkAgg(fig, master=frame_grafica)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Crear la ventana principal
root = tk.Tk()
root.title("Visualizador de Temperaturas CSV")

# Botón para cargar archivo
btn_cargar = tk.Button(root, text="Cargar archivo CSV", command=cargar_csv)
btn_cargar.pack(pady=10)

# Frame para la gráfica
frame_grafica = tk.Frame(root)
frame_grafica.pack(fill=tk.BOTH, expand=True)

# Ejecutar la interfaz
root.mainloop()
