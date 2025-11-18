import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path

def process_sma_data():
    """
    Procesador de datos para experimentos con aleaciones SMA (Shape Memory Alloy)
    Separa las fases de calentamiento y enfriamiento, aplica correcciones y genera gráficas
    """
    
    print("=== PROCESADOR DE DATOS SMA ===")
    print("Aleaciones con Memoria de Forma")
    print("-" * 40)
    
    # Solicitar información al usuario
    folder_path = "Test_bueno\\20250606_173900"  # Carpeta base
    
    # Validar que la carpeta existe
    if not os.path.exists(folder_path):
        print(f"Error: La carpeta '{folder_path}' no existe.")
        return
    
    # Buscar el archivo CSV específico
    csv_filename = "data_with_temperature.csv"
    csv_path = os.path.join(folder_path, csv_filename)
    
    if not os.path.exists(csv_path):
        print(f"Error: El archivo '{csv_filename}' no se encuentra en la carpeta especificada.")
        return
    
    # Solicitar tipo de experimento
    print("\nTipo de experimento:")
    print("1. Deflexión constante (midiendo fuerza)")
    print("2. Fuerza constante (midiendo deflexión)")
    
    while True:
        try:
            exp_choice = int(input("Selecciona el tipo de experimento (1 o 2): "))
            if exp_choice in [1, 2]:
                break
            else:
                print("Por favor, ingresa 1 o 2.")
        except ValueError:
            print("Por favor, ingresa un número válido.")
    
    # Solicitar valor del experimento
    if exp_choice == 1:
        experiment_type = "deflexion_constante"
        while True:
            try:
                experiment_value = float(input("Ingresa el valor de deflexión constante (mm): "))
                break
            except ValueError:
                print("Por favor, ingresa un valor numérico válido.")
    else:
        experiment_type = "fuerza_constante"
        while True:
            try:
                experiment_value = float(input("Ingresa el peso aplicado (gramos): "))
                break
            except ValueError:
                print("Por favor, ingresa un valor numérico válido.")
    
    print(f"\nProcesando datos del experimento: {experiment_type}")
    print(f"Valor del experimento: {experiment_value}")
    
    # Leer el archivo CSV
    try:
        df = pd.read_csv(csv_path)
        print(f"Archivo leído exitosamente. {len(df)} registros encontrados.")
    except Exception as e:
        print(f"Error al leer el archivo CSV: {e}")
        return
    
    # Aplicar correcciones a los datos
    print("\nAplicando correcciones...")
    
    # Corrección de deflexión: restar 30mm (diámetro marcadores) y 167mm (longitud original)
    df['deflexion_corregida_mm'] = df['distancia_raw_mm'] - 30 - 167
    
    # Corrección de fuerza
    if experiment_type == "fuerza_constante":
        # Para experimento de fuerza constante: (peso_g - 50g) / 101.97
        fuerza_corregida_N = (experiment_value - 50) / 101.97
        df['fuerza_corregida_N'] = fuerza_corregida_N
        valor_aplicado = fuerza_corregida_N
        unidad_aplicada = "N"
    else:
        # Para experimento de deflexión constante: usar la fuerza medida
        df['fuerza_corregida_N'] = df['force_N_mod']
        valor_aplicado = experiment_value
        unidad_aplicada = "mm"
    
    # Separar fases de calentamiento y enfriamiento
    print("Separando fases de calentamiento y enfriamiento...")
    
    # Fase de calentamiento: current_mA > 0 o busVoltage_SMA_V > 0
    calentamiento = df[(df['current_mA'] > 0) | (df['busVoltage_SMA_V'] > 0)].copy()
    
    # Fase de enfriamiento: current_mA = 0 y busVoltage_SMA_V = 0
    enfriamiento = df[(df['current_mA'] == 0) & (df['busVoltage_SMA_V'] == 0)].copy()
    
    print(f"Fase de calentamiento: {len(calentamiento)} registros")
    print(f"Fase de enfriamiento: {len(enfriamiento)} registros")
    
    # Función para agrupar por temperatura y promediar
    def group_and_average(data, phase_name):
        if len(data) == 0:
            print(f"Advertencia: No hay datos para la fase de {phase_name}")
            return pd.DataFrame()
        
        # Agrupar por temperatura y calcular promedio
        grouped = data.groupby('temperature').agg({
            'current_mA': 'mean',
            'force_N': 'mean',
            'busVoltage_SMA_V': 'mean',
            'busVoltage_ref_V': 'mean',
            'deflexion_corregida_mm': 'mean',
            'fuerza_corregida_N': 'mean',
            'force_N_mod': 'mean'
        }).reset_index()
        
        # Agregar información adicional
        grouped['fase'] = phase_name
        grouped['tipo_experimento'] = experiment_type
        grouped['valor_aplicado'] = valor_aplicado
        grouped['unidad_aplicada'] = unidad_aplicada
        
        # Contar observaciones por temperatura
        count_per_temp = data.groupby('temperature').size().reset_index(name='num_observaciones')
        grouped = grouped.merge(count_per_temp, on='temperature')
        
        # Ordenar por temperatura
        grouped = grouped.sort_values('temperature')
        
        return grouped
    
    # Procesar ambas fases
    calentamiento_procesado = group_and_average(calentamiento, 'calentamiento')
    enfriamiento_procesado = group_and_average(enfriamiento, 'enfriamiento')
    
    #print(f"Temperaturas únicas en calentamiento: {len(calentamiento_procesado)}")
    #print(f"Temperaturas únicas en enfriamiento: {len(enfriamiento_procesado)}")
    
    # Guardar archivos CSV
    print("\nGuardando archivos CSV...")
    
    # Nombres de archivos de salida
    calentamiento_filename = "sma_calentamiento.csv"
    enfriamiento_filename = "sma_enfriamiento.csv"
    
    calentamiento_path = os.path.join(folder_path, calentamiento_filename)
    enfriamiento_path = os.path.join(folder_path, enfriamiento_filename)
    
    # Guardar datos procesados
    if not calentamiento_procesado.empty:
        calentamiento_procesado.to_csv(calentamiento_path, index=False)
        print(f"Archivo guardado: {calentamiento_path}")
    
    if not enfriamiento_procesado.empty:
        enfriamiento_procesado.to_csv(enfriamiento_path, index=False)
        print(f"Archivo guardado: {enfriamiento_path}")
    
    # Generar gráfica
    print("\nGenerando gráfica...")
    
    plt.figure(figsize=(12, 8))
    
    # Configurar título y etiquetas según el tipo de experimento
    if experiment_type == "fuerza_constante":
        # Graficar temperatura vs deflexión
        y_label = "Deflexión Corregida (mm)"
        titulo = f"Experimento SMA - Fuerza Constante ({valor_aplicado:.3f} {unidad_aplicada})"
        
        if not calentamiento_procesado.empty:
            plt.plot(calentamiento_procesado['temperature'], 
                    calentamiento_procesado['deflexion_corregida_mm'], 
                    'ro-', label='Calentamiento', linewidth=2, markersize=6)
        
        if not enfriamiento_procesado.empty:
            plt.plot(enfriamiento_procesado['temperature'], 
                    enfriamiento_procesado['deflexion_corregida_mm'], 
                    'bo-', label='Enfriamiento', linewidth=2, markersize=6)
    
    else:  # deflexion_constante
        # Graficar temperatura vs fuerza
        y_label = "Fuerza Corregida (N)"
        titulo = f"Experimento SMA - Deflexión Constante ({valor_aplicado} {unidad_aplicada})"
        
        if not calentamiento_procesado.empty:
            plt.plot(calentamiento_procesado['temperature'], 
                    calentamiento_procesado['fuerza_corregida_N'], 
                    'ro-', label='Calentamiento', linewidth=2, markersize=6)
        
        if not enfriamiento_procesado.empty:
            plt.plot(enfriamiento_procesado['temperature'], 
                    enfriamiento_procesado['fuerza_corregida_N'], 
                    'bo-', label='Enfriamiento', linewidth=2, markersize=6)
    
    # Configurar la gráfica
    plt.xlabel('Temperatura (°C)', fontsize=12)
    plt.ylabel(y_label, fontsize=12)
    plt.title(titulo, fontsize=14, fontweight='bold')
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    
    # Mejorar el estilo
    plt.tight_layout()
    
    # Guardar la gráfica
    graph_filename = f"sma_grafica_{experiment_type}.png"
    graph_path = os.path.join(folder_path, graph_filename)
    
    plt.savefig(graph_path, dpi=300, bbox_inches='tight')
    print(f"Gráfica guardada: {graph_path}")
    
    # Mostrar la gráfica
    plt.show()
    
    # Resumen final
    print("\n" + "="*50)
    print("RESUMEN DEL PROCESAMIENTO")
    print("="*50)
    print(f"Tipo de experimento: {experiment_type}")
    print(f"Valor aplicado: {valor_aplicado} {unidad_aplicada}")
    print(f"Registros originales: {len(df)}")
    print(f"Registros calentamiento: {len(calentamiento)} → {len(calentamiento_procesado)} temperaturas únicas")
    print(f"Registros enfriamiento: {len(enfriamiento)} → {len(enfriamiento_procesado)} temperaturas únicas")
    print(f"\nArchivos generados en: {folder_path}")
    print(f"- {calentamiento_filename}")
    print(f"- {enfriamiento_filename}")
    print(f"- {graph_filename}")
    print("\nProcesamiento completado exitosamente!")

if __name__ == "__main__":
    try:
        process_sma_data()
    except KeyboardInterrupt:
        print("\n\nProceso interrumpido por el usuario.")
    except Exception as e:
        print(f"\nError inesperado: {e}")
        print("Por favor, verifica los datos de entrada e intenta nuevamente.")