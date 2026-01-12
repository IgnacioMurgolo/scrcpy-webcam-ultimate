# 📸 Scrcpy Webcam Ultimate

Herramienta gráfica para Linux que transforma tu dispositivo Android en una Webcam profesional de alta definición para Discord, Zoom, Meet, OBS, etc., utilizando el motor de scrcpy y el driver v4l2loopback.

## 🚀 Características Principales
* **Detección de Lentes:** Escanea automáticamente el hardware del dispositivo para permitir la selección entre cámara frontal, trasera o lentes auxiliares (Macro/Gran angular).
* **Auto-Instalable:** Descarga `scrcpy` automáticamente si no lo tenés.
* **Acceso Directo Automático:** Al iniciar por primera vez, crea lanzadores en el Escritorio y en el Menú de Aplicaciones de Linux.
* **Conexión Híbrida:** Soporta conexión vía USB para mínima latencia y vía WiFi (ADB TCP/IP) para movilidad total.
* **Ajuste Inteligente:** Control de bitrate y resolución (720p/1080p) con protección de ancho de banda para evitar artefactos visuales.
* **Interfaz Moderna:** Desarrollada con `CustomTkinter` para una experiencia de usuario fluida en Linux.
* **Modo Espejo:** Opción de volteo de imagen (Flip) integrada para videollamadas.
* **Eficiencia:** Basado en el motor de **scrcpy**, garantizando el menor uso de CPU posible.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/Linux-Mint%2FUbuntu-orange)

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
pip install -r requirements.txt
```

### 4. Ejecución
Con el celular conectado por USB y la Depuración USB activada:
```bash
python main.py
```
Nota: Al ejecutarlo, se crearán automáticamente los accesos directos en tu sistema.

## 🧹 Desinstalación
Si deseas eliminar los accesos directos creados en el Menú y el Escritorio, ejecutá:
```bash
python main.py --uninstall

=======
```
>>>>>>> 765b412 (Agrega funcion de usar mic, correccion de errores y mejora UI. Se hace refactoreo.)
