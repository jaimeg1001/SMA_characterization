import cv2
import pytesseract
import pandas as pd
import os
import re
from pathlib import Path

# Configurar la ruta de Tesseract
pytesseract.pytesseract.tesseract_cmd = 'C:/Program Files/Tesseract-OCR/tesseract.exe'

def extract_temperature_from_image(image_path, roi_x1=260, roi_y1=10, size_x=120, size_y=40, thresh=240, show_roi=False):
    """
    Extrae la temperatura de una imagen usando OCR en una región específica (ROI)
    
    Args:
        image_path: Ruta de la imagen
        roi_x1, roi_y1: Coordenadas de inicio del ROI
        size_x, size_y: Tamaño del ROI
        thresh: Umbral para binarización
        show_roi: Si True, muestra la imagen con el ROI marcado
    
    Returns:
        float: Valor numérico de temperatura o None si no se puede extraer
    """
    try:
        # Leer la imagen
        frame = cv2.imread(image_path)
        if frame is None:
            print(f"Error: No se pudo cargar la imagen {image_path}")
            return None
        
        # Si se solicita visualización, mostrar la imagen con el ROI
        if show_roi:
            frame_display = frame.copy()
            # Dibujar rectángulo del ROI
            cv2.rectangle(frame_display, (roi_x1, roi_y1), (roi_x1+size_x, roi_y1+size_y), (0, 255, 0), 2)
            # Agregar texto con las coordenadas
            cv2.putText(frame_display, f'ROI: ({roi_x1},{roi_y1}) {size_x}x{size_y}', 
                       (roi_x1, roi_y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Mostrar imagen completa
            cv2.imshow('Imagen con ROI', frame_display)
            
        # Extraer ROI
        roi = frame[roi_y1:roi_y1+size_y, roi_x1:roi_x1+size_x]
        
        # Convertir a escala de grises
        roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Binarizar
        roi_bw = cv2.threshold(roi_gray, thresh, 255, cv2.THRESH_BINARY)[1]
        
        # Si se solicita visualización, mostrar el ROI procesado
        if show_roi:
            cv2.imshow('ROI Original', roi)
            cv2.imshow('ROI Escala de Grises', roi_gray)
            cv2.imshow('ROI Binarizado', roi_bw)
            
            print(f"Presiona cualquier tecla para continuar con la siguiente imagen...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
        # Extraer texto con OCR
        text = pytesseract.image_to_string(roi_bw, config='--psm 8 -c tessedit_char_whitelist=0123456789.-')
        
        # Extraer solo el valor numérico
        temperature = extract_numeric_value(text)
        
        return temperature
        
    except Exception as e:
        print(f"Error procesando {image_path}: {e}")
        return None

def extract_numeric_value(text):
    """
    Extrae el valor numérico de temperatura del texto OCR
    
    Args:
        text: Texto extraído por OCR
    
    Returns:
        float: Valor numérico o None si no se encuentra
    """
    # Limpiar el texto
    text = text.strip().replace('\n', '').replace(' ', '')
    
    # Buscar patrones numéricos (puede incluir decimales y signo negativo)
    pattern = r'-?\d+\.?\d*'
    matches = re.findall(pattern, text)
    
    if matches:
        try:
            # Tomar el primer valor numérico encontrado
            return float(matches[0])
        except ValueError:
            pass
    
    return None

def process_csv_with_temperature(csv_path, images_folder='cam2', output_csv=None, show_roi=False, roi_params=None):
    """
    Procesa el CSV agregando la columna de temperatura extraída de las imágenes
    
    Args:
        csv_path: Ruta del archivo CSV
        images_folder: Carpeta que contiene las imágenes
        output_csv: Ruta del archivo CSV de salida (opcional)
        show_roi: Si True, muestra el ROI para cada imagen
        roi_params: Diccionario con parámetros del ROI (roi_x1, roi_y1, size_x, size_y, thresh)
    """
    try:
        # Configurar parámetros del ROI
        if roi_params is None:
            roi_params = {
                'roi_x1': 260,
                'roi_y1': 10,
                'size_x': 120,
                'size_y': 40,
                'thresh': 240
            }
        
        # Leer el CSV
        df = pd.read_csv(csv_path)
        print(f"CSV cargado con {len(df)} filas")
        
        # Verificar que existe la columna timestamp
        if 'timestamp' not in df.columns:
            print("Error: No se encontró la columna 'timestamp' en el CSV")
            return
        
        # Verificar que existe la carpeta de imágenes
        images_path = Path(images_folder)
        if not images_path.exists():
            print(f"Error: No se encontró la carpeta {images_folder}")
            return
        
        # Lista para almacenar las temperaturas
        temperatures = []
        
        print("Procesando imágenes...")
        if show_roi:
            print("MODO VISUALIZACIÓN: Se mostrará el ROI para cada imagen")
            print("Presiona cualquier tecla para avanzar a la siguiente imagen")
        
        # Procesar cada timestamp
        for idx, timestamp in enumerate(df['timestamp']):
            print(f"Procesando {idx+1}/{len(df)}: {timestamp}")
            
            # Construir la ruta de la imagen
            image_filename = f"{timestamp}.jpg"
            image_path = images_path / image_filename
            
            # Extraer temperatura
            if image_path.exists():
                temperature = extract_temperature_from_image(
                    str(image_path), 
                    show_roi=show_roi,
                    **roi_params
                )
                temperatures.append(temperature)
                
                if temperature is not None:
                    print(f"  -> Temperatura extraída: {temperature}")
                else:
                    print(f"  -> No se pudo extraer temperatura")
            else:
                print(f"  -> Imagen no encontrada: {image_path}")
                temperatures.append(None)
        
        # Agregar la columna de temperatura al DataFrame
        df['temperature'] = temperatures
        
        # Guardar el resultado en la misma carpeta que el CSV original
        if output_csv is None:
            csv_dir = Path(csv_path).parent
            csv_name = Path(csv_path).stem
            output_csv = csv_dir / f"{csv_name}_with_temperature.csv"
        
        df.to_csv(output_csv, index=False)
        print(f"\nResultado guardado en: {output_csv}")
        
        # Mostrar estadísticas
        valid_temps = [t for t in temperatures if t is not None]
        print(f"\nEstadísticas:")
        print(f"- Total de imágenes procesadas: {len(temperatures)}")
        print(f"- Temperaturas extraídas exitosamente: {len(valid_temps)}")
        print(f"- Temperaturas fallidas: {len(temperatures) - len(valid_temps)}")
        
        if valid_temps:
            print(f"- Temperatura promedio: {sum(valid_temps)/len(valid_temps):.2f}")
            print(f"- Temperatura mínima: {min(valid_temps):.2f}")
            print(f"- Temperatura máxima: {max(valid_temps):.2f}")
        
        return df
        
    except Exception as e:
        print(f"Error procesando el CSV: {e}")
        return None

def adjust_roi_interactively(sample_image_path):
    """
    Función interactiva para ajustar el ROI visualmente
    
    Args:
        sample_image_path: Ruta de una imagen de muestra para ajustar el ROI
    
    Returns:
        dict: Parámetros del ROI ajustados
    """
    print("\n=== MODO AJUSTE INTERACTIVO DE ROI ===")
    
    # Parámetros iniciales
    roi_params = {
        'roi_x1': 260,
        'roi_y1': 10,
        'size_x': 120,
        'size_y': 40,
        'thresh': 240
    }
    
    # Cargar imagen de muestra
    frame = cv2.imread(sample_image_path)
    if frame is None:
        print(f"Error: No se pudo cargar la imagen {sample_image_path}")
        return roi_params
    
    print("Instrucciones:")
    print("- Usa las teclas para ajustar el ROI:")
    print("  w/s: mover ROI arriba/abajo")
    print("  a/d: mover ROI izquierda/derecha") 
    print("  q/e: hacer ROI más pequeño/grande (ancho)")
    print("  r/t: hacer ROI más pequeño/grande (alto)")
    print("  z/x: disminuir/aumentar umbral de binarización")
    print("  ENTER: confirmar y usar estos valores")
    print("  ESC: cancelar y usar valores por defecto")
    
    while True:
        # Crear copia de la imagen
        frame_display = frame.copy()
        
        # Dibujar ROI
        x1, y1 = roi_params['roi_x1'], roi_params['roi_y1']
        x2, y2 = x1 + roi_params['size_x'], y1 + roi_params['size_y']
        
        cv2.rectangle(frame_display, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Agregar texto con información
        info_text = f"ROI: ({x1},{y1}) {roi_params['size_x']}x{roi_params['size_y']} | Thresh: {roi_params['thresh']}"
        cv2.putText(frame_display, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Extraer y procesar ROI para mostrar resultado
        if y1 >= 0 and x1 >= 0 and y2 < frame.shape[0] and x2 < frame.shape[1]:
            roi = frame[y1:y2, x1:x2]
            if roi.size > 0:
                roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                roi_bw = cv2.threshold(roi_gray, roi_params['thresh'], 255, cv2.THRESH_BINARY)[1]
                
                # Hacer el ROI más grande para visualización
                roi_display = cv2.resize(roi_bw, (roi_params['size_x']*3, roi_params['size_y']*3), interpolation=cv2.INTER_NEAREST)
                
                # Extraer texto
                text = pytesseract.image_to_string(roi_bw, config='--psm 8 -c tessedit_char_whitelist=0123456789.-')
                temp_value = extract_numeric_value(text)
                
                # Mostrar resultado OCR
                cv2.putText(frame_display, f"OCR: {text.strip()} -> Temp: {temp_value}", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                
                cv2.imshow('ROI Binarizado (3x)', roi_display)
        
        cv2.imshow('Ajuste de ROI', frame_display)
        
        key = cv2.waitKey(30) & 0xFF
        
        # Controles de movimiento
        if key == ord('w'):  # Arriba
            roi_params['roi_y1'] = max(0, roi_params['roi_y1'] - 5)
        elif key == ord('s'):  # Abajo
            roi_params['roi_y1'] = min(frame.shape[0] - roi_params['size_y'], roi_params['roi_y1'] + 5)
        elif key == ord('a'):  # Izquierda
            roi_params['roi_x1'] = max(0, roi_params['roi_x1'] - 5)
        elif key == ord('d'):  # Derecha
            roi_params['roi_x1'] = min(frame.shape[1] - roi_params['size_x'], roi_params['roi_x1'] + 5)
        elif key == ord('q'):  # Ancho menor
            roi_params['size_x'] = max(20, roi_params['size_x'] - 5)
        elif key == ord('e'):  # Ancho mayor
            roi_params['size_x'] = min(200, roi_params['size_x'] + 5)
        elif key == ord('r'):  # Alto menor
            roi_params['size_y'] = max(10, roi_params['size_y'] - 5)
        elif key == ord('t'):  # Alto mayor
            roi_params['size_y'] = min(100, roi_params['size_y'] + 5)
        elif key == ord('z'):  # Threshold menor
            roi_params['thresh'] = max(50, roi_params['thresh'] - 10)
        elif key == ord('x'):  # Threshold mayor
            roi_params['thresh'] = min(255, roi_params['thresh'] + 10)
        elif key == 13:  # Enter
            print("ROI ajustado confirmado!")
            break
        elif key == 27:  # Escape
            print("Ajuste cancelado, usando valores por defecto")
            roi_params = {
                'roi_x1': 260,
                'roi_y1': 10,
                'size_x': 120,
                'size_y': 40,
                'thresh': 240
            }
            break
    
    cv2.destroyAllWindows()
    print(f"Parámetros finales del ROI: {roi_params}")
    return roi_params

def main():
    """Función principal"""
    # Configuración - ajustada para la estructura de carpetas
    base_folder = "RESORTES_10_15_Res\\400\\110\\20250708_141511"  # Carpeta base
    csv_file = os.path.join(base_folder, "data.csv")
    images_folder = os.path.join(base_folder, "cam2")
    
    # Verificar que existe el archivo CSV
    if not os.path.exists(csv_file):
        print(f"Error: No se encontró el archivo {csv_file}")
        return
    
    # Verificar que existe la carpeta de imágenes
    if not os.path.exists(images_folder):
        print(f"Error: No se encontró la carpeta {images_folder}")
        return
    
    # Preguntar al usuario qué modo usar
    print("Selecciona el modo de operación:")
    print("1. Procesamiento normal (usa ROI por defecto)")
    print("2. Ajustar ROI interactivamente primero")
    print("3. Procesar con visualización del ROI (para verificar)")
    
    while True:
        try:
            choice = input("Ingresa tu opción (1-3): ").strip()
            if choice in ['1', '2', '3']:
                break
            else:
                print("Por favor ingresa 1, 2 o 3")
        except KeyboardInterrupt:
            print("\nOperación cancelada")
            return
    
    roi_params = None
    show_roi = False
    
    if choice == '2':
        # Encontrar una imagen de muestra
        sample_images = list(Path(images_folder).glob("*.jpg"))
        if not sample_images:
            print("No se encontraron imágenes JPG en la carpeta")
            return
        
        sample_image = str(sample_images[0])
        print(f"Usando imagen de muestra: {sample_image}")
        roi_params = adjust_roi_interactively(sample_image)
        
    elif choice == '3':
        show_roi = True
    
    # Procesar
    print("Iniciando procesamiento...")
    result_df = process_csv_with_temperature(csv_file, images_folder, show_roi=show_roi, roi_params=roi_params)
    
    if result_df is not None:
        print("\n¡Procesamiento completado exitosamente!")
        
        # Mostrar las primeras filas del resultado
        print("\nPrimeras 5 filas del resultado:")
        print(result_df.head())
    else:
        print("\nError en el procesamiento")

if __name__ == "__main__":
    main()