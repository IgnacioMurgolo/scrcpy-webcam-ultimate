# 📸 Scrcpy Webcam Ultimate

Este proyecto transforma un dispositivo Android en una Webcam de alta definición para Linux, utilizando el motor de **scrcpy** y el driver **v4l2loopback**. 

Fue diseñado originalmente para optimizar el uso de un **Xiaomi Redmi Note 5 (Whyred)**, pero es compatible con cualquier dispositivo Android moderno (especialmente Android 11+ para funciones nativas de cámara y audio).

## 🚀 Características Principales
* **Detección de Lentes:** Escanea automáticamente el hardware del dispositivo para permitir la selección entre cámara frontal, trasera o lentes auxiliares (Macro/Gran angular).
* **Conexión Híbrida:** Soporta conexión vía USB para mínima latencia y vía WiFi (ADB TCP/IP) para movilidad total.
* **Audio Integrado:** Opción para habilitar el micrófono del celular de forma nativa (Android 11+).
* **Ajuste Inteligente:** Control de bitrate y resolución (720p/1080p) con protección de ancho de banda para evitar artefactos visuales.
* **Interfaz Moderna:** Desarrollada con `CustomTkinter` para una experiencia de usuario fluida en Linux.

## 📦 Instalación y Configuración

### 1. Dependencias del Sistema
Primero, instalá las herramientas necesarias en tu distribución basada en Debian/Ubuntu (como Linux Mint):
```bash
sudo apt update
sudo apt install adb v4l2loopback-dkms python3-tk
```

### 2. Configuración del Driver de Video
Para que el sistema reconozca el celular como una cámara web, necesitamos activar el módulo de video virtual:
```bash
sudo modprobe v4l2loopback exclusive_caps=1 card_label="Webcam-Pro" video_nr=10
```

### 3. Entorno de Python
Se recomienda usar un entorno virtual para mantener limpia tu instalación:
```bash
# Clonar y entrar al repo
git clone [https://github.com/IgnacioMurgolo/scrcpy-webcam-ultimate.git](https://github.com/IgnacioMurgolo/scrcpy-webcam-ultimate.git)
cd scrcpy-webcam-ultimate

# Crear y activar venv
python3 -m venv venv
source venv/bin/activate

# Instalar librerías
pip install -r requeriments.txt
```

### 4. Ejecución
Con el celular conectado por USB y la Depuración USB activada:
```bash
python main.py
```

