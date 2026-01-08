# 📸 Scrcpy Webcam Ultimate

Este proyecto transforma un dispositivo Android en una Webcam de alta definición para Linux, utilizando el motor de **scrcpy** y el driver **v4l2loopback**. 

Fue diseñado originalmente para optimizar el uso de un **Xiaomi Redmi Note 5 (Whyred)**, pero es compatible con cualquier dispositivo Android moderno (especialmente Android 11+ para funciones nativas de cámara y audio).

## 🚀 Características Principales
* **Detección de Lentes:** Escanea automáticamente el hardware del dispositivo para permitir la selección entre cámara frontal, trasera o lentes auxiliares (Macro/Gran angular).
* **Conexión Híbrida:** Soporta conexión vía USB para mínima latencia y vía WiFi (ADB TCP/IP) para movilidad total.
* **Audio Integrado:** Opción para habilitar el micrófono del celular de forma nativa (Android 11+).
* **Ajuste Inteligente:** Control de bitrate y resolución (720p/1080p) con protección de ancho de banda para evitar artefactos visuales.
* **Interfaz Moderna:** Desarrollada con `CustomTkinter` para una experiencia de usuario fluida en Linux.

## 🛠️ Requisitos del Sistema
Para funcionar en Linux Mint / Ubuntu, el sistema requiere:
* `adb` (Android Debug Bridge)
* `v4l2loopback-dkms` (Para crear el dispositivo de video virtual `/dev/video10`)
* `python3-tk` y las librerías listadas en `requirements.txt`

## 📦 Instalación y Uso
1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/IgnacioMurgolo/scrcpy-webcam-ultimate.git](https://github.com/IgnacioMurgolo/scrcpy-webcam-ultimate.git)
   cd scrcpy-webcam-ultimate
