import pandas as pd
import matplotlib.pyplot as plt
import os

# === SETTINGS ===
csv_path = 'testFolder\\20250425_181756\\data.csv'  # <-- Change to your real path
save_fig_name = 'temperature_vs_deflexion_force.png'

# === Load data ===
df = pd.read_csv(csv_path)

# === Detect Heating / Cooling ===
# Heating: current_mA != 0
# Cooling: current_mA == 0
heating = df[df['current_mA'] != 0]
cooling = df[df['current_mA'] == 0]

# === Variables to process ===
temp_points = ['temp_point1', 'temp_point2', 'temp_point3']
y_variables = ['deflexion_mm', 'force_N']

# === Create Figure and Axes ===
fig, axs = plt.subplots(nrows=3, ncols=2, figsize=(14, 18))
fig.subplots_adjust(hspace=0.4, wspace=0.3)

for i, temp_point in enumerate(temp_points):
    for j, y_var in enumerate(y_variables):
        
        ax = axs[i, j]
        
        # --- Heating data ---
        heat_group = heating.groupby(temp_point)[y_var].mean()
        heat_group = heat_group.sort_index()  # Sort by temperature
        
        ax.plot(heat_group.index, heat_group.values, 
                color='red', marker='o', label='Heating')
        
        # --- Cooling data ---
        cool_group = cooling.groupby(temp_point)[y_var].mean()
        cool_group = cool_group.sort_index()
        
        ax.plot(cool_group.index, cool_group.values, 
                color='blue', marker='s', label='Cooling')
        
        # --- Titles and labels ---
        ax.set_title(f'{temp_point}: {y_var} vs Temperature')
        ax.set_xlabel('Temperature (°C)')
        ax.set_ylabel(y_var)
        ax.grid(True)
        ax.legend()

# === Save the figure ===
save_dir = os.path.dirname(csv_path)
save_path = os.path.join(save_dir, save_fig_name)
plt.savefig(save_path)
print(f"Figure saved at: {save_path}")

plt.show()
