%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%              Suvizador de curvas               %%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Inicialización
clc
clear all
% Importar Datos
data_heat = readtable("Test_bueno\20250606_161450\sma_calentamiento.csv");
data_cool = readtable("Test_bueno\20250606_161450\sma_enfriamiento.csv");

% Selecciona el tipo de experimento
% 0 : def - const   |   fza - var
% 1 : def - var     |   fza - const

experimento = 1;

if experimento
    y_data_heat = data_heat.deflexion_corregida_mm;
    y_data_cool = data_cool.deflexion_corregida_mm;
else
    y_data_heat = data_heat.fuerza_corregida_N;
    y_data_cool = data_cool.fuerza_corregida_N;
end

x_data_heat = data_heat.temperature;
x_data_cool = data_cool.temperature;

% Muestra la grafica de la información sin suavizar

figure();
hold on
if experimento
    title('Deflection vs Temperature, Weigth: 0.981 N','FontSize',25)
    ylabel('Deflexión (mm)','FontSize',25)
else
    title('Force vs Temperature, Deflection: 50 mm','FontSize',25)
    ylabel('Output Force (N)','FontSize',25)
end
xlabel('Temperature (°C)','FontSize',25)

% Suavizado de la información

[y_smooth_heat,window] = smoothdata(y_data_heat,"movmean",3);
[y_smooth_cool,window] = smoothdata(y_data_cool,"movmean",3);

plot(x_data_heat,y_smooth_heat,'*r','LineWidth',3)
plot(x_data_cool,y_smooth_cool,'*b','LineWidth',3)
%plot(x_data_heat,y_data_heat,'*r','MarkerSize',6)
%plot(x_data_cool,y_data_cool,'*b','MarkerSize',6)
axis tight
legend("dT/dt>0","dT/dt<0",'Fontsize',25,"location","best")
%legend("Datos suavizados dT/dt>0","Datos suavizados dT/dt<0","Datos medidos dT/dt>0","Datos medidos dT/dt<0",'Fontsize',25,"location","best")
grid on
fontsize(gca, 25,'points')