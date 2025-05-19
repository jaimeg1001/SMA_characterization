# SMA Characterization

This project provides a complete setup for the characterization of Shape Memory Alloys (SMA) using various sensors and cameras. The setup is composed of four main applications, each serving a specific purpose:

## Applications

1. **mainGUI**

   * A graphical user interface application developed in PyQt5 for real-time data acquisition.
   * Connects to an Arduino and two USB cameras for synchronized data capture.
   * Receives data from sensors and stores it in a CSV file, along with captured images.

2. **SMACircuitVF (Arduino Code)**

   * Manages sensor readings (force, current/voltage, and temperature).
   * Sends data via serial communication to the PyQt5 application (guiMain).

3. **temperatureStimation**

   * Analyzes captured images to estimate temperature using RGB values.
   * Provides temperature values based on the color information in the images.

4. **plotSMA**

   * Plots graphs for temperature-force and temperature-deflection based on the acquired data.

## Hardware Components

* Arduino board
* Force sensor (Vernier)
* Current/Voltage sensor (INA219)
* Temperature images (Fluke Ti401 pro)
* PWM-controlled fan
* Two USB cameras

## Software Stack

* Python (PyQt5 for GUI, OpenCV for image processing, Matplotlib for plotting)
* Arduino IDE for SMACircuitVF

## Installation

1. Clone this repository:

```bash
 git clone https://github.com/jaimeg1001/SMA-Characterization.git
```

2. Install Python dependencies:

```bash
 pip install -r requirements.txt
```

3. Upload SMACircuitVF to the Arduino using the Arduino IDE.

## Usage

1. Launch guiMain for data acquisition.
2. Connect the Arduino and ensure sensor connections are correct.
3. Run temperatureStimation to process captured images.
4. Use plotSMA to generate the required graphs.

## Future Improvements

* Enhanced temperature estimation algorithm.
* Additional sensor support.
* Real-time plotting integration.

## Authors

* Jaime Guzman - [jaimeg1001](https://github.com/jaimeg1001)
