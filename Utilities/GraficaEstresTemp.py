import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Configuración de matplotlib para gráficos en español
plt.rcParams['font.size'] = 14
plt.rcParams['figure.figsize'] = (12, 8)

# Parámetros para cálculos
D = 6e-3  # 6 mm en metros
d = 1e-3  # 1 mm en metros
n = 142
C = 6
k = (4*C - 1)/(4*C - 4) + 0.615/C  # Factor de corrección

print(f"Factor de corrección k = {k:.4f}")

# Cargar datos
def load_data():
    """Carga todos los archivos CSV"""
    data = {}
    
    # Definir deflexiones para cada conjunto de datos
    deflections = {
        'Test_bueno\\20250606_124200': 100,  # 100 deflexión
        'Test_bueno\\20250606_131214': 50,   # 50 deflexión  
        'Test_bueno\\20250606_150502': 115,  # 115 deflexión
        'Test_bueno\\20250606_152921': 85,   # 85 deflexión
        'Test_bueno\\20250606_154922': 35    # 35 deflexión
    }
    
    for path, deflection in deflections.items():
        try:
            heat_file = f"{path}\\sma_calentamiento.csv"
            cool_file = f"{path}\\sma_enfriamiento.csv"
            
            data_heat = pd.read_csv(heat_file)
            data_cool = pd.read_csv(cool_file)
            
            # Agregar columna de deflexión
            data_heat['deflexion'] = deflection
            data_cool['deflexion'] = deflection
            
            data[f'heat_{deflection}'] = data_heat
            data[f'cool_{deflection}'] = data_cool
            
            print(f"Cargado: deflexión {deflection} mm")
            
        except FileNotFoundError as e:
            print(f"Archivo no encontrado: {e}")
            
    return data

# Función para crear gráficas de temperatura vs fuerza
def plot_temperature_force(data):
    """Grafica temperatura vs fuerza para cada deflexión en un solo plot"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    deflections = [35, 50, 85, 100, 115]
    colors = ['blue', 'green', 'red', 'orange', 'purple']
    
    # Gráfica de calentamiento
    for i, deflection in enumerate(deflections):
        key = f'heat_{deflection}'
        if key in data:
            df = data[key]
            ax.plot(df['temperature'], df['fuerza_corregida_N'], 
                   color=colors[i], label=f'Calentamiento - Deflexión {deflection} mm', 
                   linewidth=2, marker='o', markersize=3, linestyle='-')
    
    # Gráfica de enfriamiento
    for i, deflection in enumerate(deflections):
        key = f'cool_{deflection}'
        if key in data:
            df = data[key]
            ax.plot(df['temperature'], df['fuerza_corregida_N'], 
                   color=colors[i], label=f'Enfriamiento - Deflexión {deflection} mm', 
                   linewidth=2, marker='s', markersize=3, linestyle='--')
    
    ax.set_xlabel('Temperatura (°C)',fontsize=20)
    ax.set_ylabel('Fuerza (N)',fontsize=20)
    ax.set_title('Curvas Temperatura contra Fuerza para una actuador SMA a distintas deflexiones.',fontsize=25)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

# Función para separar fases y graficar fuerza vs deflexión
def plot_force_deflection_phases(data):
    """Grafica fuerza contra deflexión para fases martensítica y austenítica"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Recopilar datos por fase
    martensite_data = []
    austenite_data = []
    
    deflections = [35, 50, 85, 100, 115]
    
    for deflection in deflections:
        # Procesar datos de calentamiento y enfriamiento
        for phase in ['heat', 'cool']:
            key = f'{phase}_{deflection}'
            if key in data:
                df = data[key]
                
                # Fase martensítica (20-35°C)
                martensite_mask = (df['temperature'] >= 20) & (df['temperature'] <= 35)
                if martensite_mask.any():
                    martensite_force = df[martensite_mask]['fuerza_corregida_N'].mean()
                    martensite_data.append({'deflexion': deflection, 'fuerza': martensite_force})
                
                # Fase austenítica (55°C en adelante)
                austenite_mask = df['temperature'] >= 55
                if austenite_mask.any():
                    austenite_force = df[austenite_mask]['fuerza_corregida_N'].mean()
                    austenite_data.append({'deflexion': deflection, 'fuerza': austenite_force})
    
    # Convertir a DataFrames
    df_martensite = pd.DataFrame(martensite_data)
    df_austenite = pd.DataFrame(austenite_data)
    
    # Agrupar por deflexión y promediar
    if not df_martensite.empty:
        df_martensite = df_martensite.groupby('deflexion')['fuerza'].mean().reset_index()
        ax.plot(df_martensite['deflexion'], df_martensite['fuerza'], 
                'bo-', linewidth=2, markersize=8, label='Fase Martensítica (<35°C)')
    
    if not df_austenite.empty:
        df_austenite = df_austenite.groupby('deflexion')['fuerza'].mean().reset_index()
        ax.plot(df_austenite['deflexion'], df_austenite['fuerza'], 
                'ro-', linewidth=2, markersize=8, label='Fase Austenítica (≥55°C)')
    
    ax.set_xlabel('Deflexión (mm)',fontsize=20)
    ax.set_ylabel('Fuerza Promedio (N)',fontsize=20)
    ax.set_title('Fuerza contra Deflexión por Fases Cristalinas',fontsize=25)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
    
    return df_martensite, df_austenite

# Función para calcular esfuerzo y deformación cortante
def calculate_shear_properties(df_martensite, df_austenite):
    """Calcula esfuerzo cortante y deformación unitaria cortante"""
    
    def calculate_properties(df, phase_name):
        if df.empty:
            return df
        
        df_calc = df.copy()
        
        # Convertir deflexión a metros
        deflection_m = df_calc['deflexion'] * 1e-3
        force_N = df_calc['fuerza']
        
        # Calcular esfuerzo cortante: τ = 8 × F × D × k / (π × d³)
        shear_stress = (8 * force_N * D * k) / (np.pi * d**3)
        
        # Calcular deformación unitaria cortante: γ = deflexión × d / (π × n × D²)
        shear_strain = (deflection_m * d) / (np.pi * n * D**2)
        
        df_calc['esfuerzo_cortante_Pa'] = shear_stress
        df_calc['deformacion_cortante'] = shear_strain
        df_calc['esfuerzo_cortante_MPa'] = shear_stress / 1e6
        
        print(f"\n{phase_name}:")
        print(f"Rango de esfuerzo cortante: {shear_stress.min()/1e6:.2f} - {shear_stress.max()/1e6:.2f} MPa")
        print(f"Rango de deformación cortante: {shear_strain.min():.6f} - {shear_strain.max():.6f}")
        
        return df_calc
    
    df_martensite_calc = calculate_properties(df_martensite, "Fase Martensítica")
    df_austenite_calc = calculate_properties(df_austenite, "Fase Austenítica")
    
    return df_martensite_calc, df_austenite_calc

# Función para graficar deformación vs esfuerzo cortante
def plot_shear_stress_strain(df_martensite, df_austenite):
    """Grafica deformación unitaria cortante contra esfuerzo cortante"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    if not df_martensite.empty:
        ax.plot(df_martensite['deformacion_cortante'], df_martensite['esfuerzo_cortante_MPa'], 
                'bo-', linewidth=2, markersize=8, label='Fase Martensítica')
        
        # Ajuste lineal para obtener módulo cortante
        if len(df_martensite) > 1:
            coeffs_m = np.polyfit(df_martensite['deformacion_cortante'], 
                                 df_martensite['esfuerzo_cortante_MPa'], 1)
            G_martensite = coeffs_m[0]  # Pendiente = Módulo cortante
            x_fit = np.linspace(df_martensite['deformacion_cortante'].min(), 
                               df_martensite['deformacion_cortante'].max(), 100)
            y_fit = coeffs_m[0] * x_fit + coeffs_m[1]
            ax.plot(x_fit, y_fit, 'b--', alpha=0.7, 
                   label=f'Ajuste Martensita (G = {G_martensite:.0f} MPa)')
    
    if not df_austenite.empty:
        ax.plot(df_austenite['deformacion_cortante'], df_austenite['esfuerzo_cortante_MPa'], 
                'ro-', linewidth=2, markersize=8, label='Fase Austenítica')
        
        # Ajuste lineal para obtener módulo cortante
        if len(df_austenite) > 1:
            coeffs_a = np.polyfit(df_austenite['deformacion_cortante'], 
                                 df_austenite['esfuerzo_cortante_MPa'], 1)
            G_austenite = coeffs_a[0]  # Pendiente = Módulo cortante
            x_fit = np.linspace(df_austenite['deformacion_cortante'].min(), 
                               df_austenite['deformacion_cortante'].max(), 100)
            y_fit = coeffs_a[0] * x_fit + coeffs_a[1]
            ax.plot(x_fit, y_fit, 'r--', alpha=0.7, 
                   label=f'Ajuste Austenita (G = {G_austenite:.0f} MPa)')
    
    ax.set_xlabel('Deformación Unitaria Cortante (γ)',fontsize=20)
    ax.set_ylabel('Esfuerzo Cortante (MPa)',fontsize=20)
    ax.set_title('Curva Esfuerzo contra Deformación Unitaria Cortante',fontsize=25)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

# NUEVA FUNCIÓN: Gráfica de esfuerzo cortante vs temperatura
def plot_stress_temperature(data):
    """Grafica esfuerzo cortante contra temperatura para cada deflexión"""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    deflections = [35, 50, 85, 100, 115]
    colors = ['blue', 'green', 'red', 'orange', 'purple']
    
    # Gráfica de calentamiento
    for i, deflection in enumerate(deflections):
        key = f'heat_{deflection}'
        if key in data:
            df = data[key]
            
            # Calcular esfuerzo cortante para cada punto
            deflection_m = deflection * 1e-3
            force_N = df['fuerza_corregida_N']
            shear_stress_MPa = (8 * force_N * D * k) / (np.pi * d**3) / 1e6
            
            ax.plot(df['temperature'], shear_stress_MPa, 
                   color=colors[i], label=f'Calentamiento - Deflexión {deflection} mm', 
                   linewidth=2, marker='o', markersize=3, linestyle='-')
    
    # Gráfica de enfriamiento
    for i, deflection in enumerate(deflections):
        key = f'cool_{deflection}'
        if key in data:
            df = data[key]
            
            # Calcular esfuerzo cortante para cada punto
            deflection_m = deflection * 1e-3
            force_N = df['fuerza_corregida_N']
            shear_stress_MPa = (8 * force_N * D * k) / (np.pi * d**3) / 1e6
            
            ax.plot(df['temperature'], shear_stress_MPa, 
                   color=colors[i], label=f'Enfriamiento - Deflexión {deflection} mm', 
                   linewidth=2, marker='s', markersize=3, linestyle='--')
    
    ax.set_xlabel('Temperatura (°C)', fontsize=20)
    ax.set_ylabel('Esfuerzo Cortante (MPa)', fontsize=20)
    ax.set_title('Curvas Esfuerzo Cortante contra Temperatura para actuador SMA a distintas deflexiones', fontsize=23)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

# Función principal
def main():
    print("=== ANÁLISIS DE MÓDULO CORTANTE EN ALEACIONES SMA ===\n")
    
    # Cargar datos
    print("1. Cargando datos...")
    data = load_data()
    
    if not data:
        print("No se pudieron cargar los datos. Verifica las rutas de los archivos.")
        return
    
    # Gráfica 1: Temperatura vs Fuerza
    print("\n2. Generando gráficas Temperatura vs Fuerza...")
    plot_temperature_force(data)
    
    # Gráfica 2: Fuerza vs Deflexión por fases
    print("\n3. Generando gráficas Fuerza vs Deflexión por fases...")
    df_martensite, df_austenite = plot_force_deflection_phases(data)
    
    # Cálculos de propiedades cortantes
    print("\n4. Calculando propiedades cortantes...")
    df_martensite_calc, df_austenite_calc = calculate_shear_properties(df_martensite, df_austenite)
    
    # Gráfica 3: Esfuerzo vs Deformación cortante
    print("\n5. Generando gráfica Esfuerzo vs Deformación cortante...")
    plot_shear_stress_strain(df_martensite_calc, df_austenite_calc)
    
    # NUEVA Gráfica 4: Esfuerzo cortante vs Temperatura
    print("\n6. Generando gráfica Esfuerzo Cortante vs Temperatura...")
    plot_stress_temperature(data)
    
    print("\n=== ANÁLISIS COMPLETADO ===")
    
    # Mostrar resumen de resultados
    if not df_martensite_calc.empty and not df_austenite_calc.empty:
        print("\nRESUMEN DE RESULTADOS:")
        print("-" * 60)
        print("Datos de la Fase Martensítica:")
        print(df_martensite_calc[['deflexion', 'fuerza', 'esfuerzo_cortante_MPa', 'deformacion_cortante']])
        
        print("\nDatos de la Fase Austenítica:")
        print(df_austenite_calc[['deflexion', 'fuerza', 'esfuerzo_cortante_MPa', 'deformacion_cortante']])
        
        print("\n" + "="*60)
        print("MÓDULO CORTANTE ESTIMADO (G = τ/γ):")
        print("="*60)
        
        # Calcular módulo cortante para cada punto - Fase Martensítica
        if not df_martensite_calc.empty:
            print("\nFASE MARTENSÍTICA:")
            print(f"{'Deflexión (mm)':<15} {'Fuerza (N)':<12} {'τ (MPa)':<12} {'γ':<12} {'G (MPa)':<12}")
            print("-" * 70)
            G_martensite_points = []
            for _, row in df_martensite_calc.iterrows():
                G_point = row['esfuerzo_cortante_MPa'] / row['deformacion_cortante']
                G_martensite_points.append(G_point)
                print(f"{row['deflexion']:<15.0f} {row['fuerza']:<12.2f} {row['esfuerzo_cortante_MPa']:<12.2f} {row['deformacion_cortante']:<12.6f} {G_point:<12.0f}")
            
            G_martensite_avg = np.mean(G_martensite_points)
            print(f"\nMódulo cortante promedio Martensítico: {G_martensite_avg:.0f} MPa")
        
        # Calcular módulo cortante para cada punto - Fase Austenítica
        if not df_austenite_calc.empty:
            print("\nFASE AUSTENÍTICA:")
            print(f"{'Deflexión (mm)':<15} {'Fuerza (N)':<12} {'τ (MPa)':<12} {'γ':<12} {'G (MPa)':<12}")
            print("-" * 70)
            G_austenite_points = []
            for _, row in df_austenite_calc.iterrows():
                G_point = row['esfuerzo_cortante_MPa'] / row['deformacion_cortante']
                G_austenite_points.append(G_point)
                print(f"{row['deflexion']:<15.0f} {row['fuerza']:<12.2f} {row['esfuerzo_cortante_MPa']:<12.2f} {row['deformacion_cortante']:<12.6f} {G_point:<12.0f}")
            
            G_austenite_avg = np.mean(G_austenite_points)
            print(f"\nMódulo cortante promedio Austenítico: {G_austenite_avg:.0f} MPa")
        
        print("\n" + "="*60)
        print("RESUMEN FINAL:")
        if not df_martensite_calc.empty:
            print(f"Módulo cortante Fase Martensítica: {G_martensite_avg:.0f} MPa")
        if not df_austenite_calc.empty:
            print(f"Módulo cortante Fase Austenítica: {G_austenite_avg:.0f} MPa")
        print("="*60)

# Ejecutar análisis
if __name__ == "__main__":
    main()