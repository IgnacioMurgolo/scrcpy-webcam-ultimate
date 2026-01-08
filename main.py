import customtkinter as ctk
import subprocess
import os
import shutil
import threading
import re
import urllib.request
import tarfile
from colorama import Fore, init

init(autoreset=True)

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRCPY_DIR = os.path.join(BASE_DIR, "scrcpy-bin")

# Lista de prioridad para buscar Scrcpy
POSIBLES_RUTAS = [
    os.path.expanduser("~/Documents/scrcpy-linux-x86_64-v3.3.4/scrcpy"),
    os.path.join(SCRCPY_DIR, "scrcpy"),
    os.path.join(SCRCPY_DIR, "scrcpy-linux-x86_64-v3.1", "scrcpy"),
    shutil.which("scrcpy")
]

SCRCPY_EXE = None 

# --- DICCIONARIO DE IDIOMAS ---
TEXTOS = {
    "es": {
        "title": "Centro de Control Webcam",
        "wifi_btn": "📶 WiFi",
        "lens": "Lente / Cámara:",
        "res": "Resolución:",
        "bitrate": "Bitrate:",
        "mirror": "Modo Espejo (Flip)",
        "preview": "Mostrar Previsualización (PC)",
        "start": "INICIAR STREAM",
        "stop": "DETENER STREAM",
        "ready": "Listo para conectar",
        "connecting": "Conectando...",
        "live": "🔴 EN VIVO",
        "wifi_success": "¡Desconectá el USB ahora!",
        "wifi_fail": "Error WiFi:",
        "finished": "Finalizado",
        "cam_rear": "Trasera (Principal)",
        "cam_front": "Frontal (Selfie)",
        "cam_aux": "Auxiliar"
    },
    "en": {
        "title": "Webcam Control Center",
        "wifi_btn": "📶 WiFi",
        "lens": "Lens / Camera:",
        "res": "Resolution:",
        "bitrate": "Bitrate:",
        "mirror": "Mirror Mode (Flip)",
        "preview": "Show Preview Window (PC)",
        "start": "START STREAM",
        "stop": "STOP STREAM",
        "ready": "Ready to connect",
        "connecting": "Connecting...",
        "live": "🔴 LIVE",
        "wifi_success": "Unplug USB now!",
        "wifi_fail": "WiFi Error:",
        "finished": "Finished",
        "cam_rear": "Back (Main)",
        "cam_front": "Front (Selfie)",
        "cam_aux": "Aux"
    }
}

# --- LÓGICA DE SISTEMA ---

def buscar_scrcpy():
    global SCRCPY_EXE
    for ruta in POSIBLES_RUTAS:
        if ruta and os.path.exists(ruta):
            if os.access(ruta, os.X_OK):
                SCRCPY_EXE = ruta
                return True
            else:
                try:
                    os.chmod(ruta, 0o755)
                    SCRCPY_EXE = ruta
                    return True
                except: pass
    return False

def check_dependencies():
    if shutil.which("adb") is None:
        print(f"{Fore.RED}[!] Error: No se encuentra 'adb'.")
        return False
    if buscar_scrcpy():
        return True
    return False

def instalador_automatico():
    if check_dependencies(): return True
    print(f"{Fore.YELLOW}[!] Scrcpy no encontrado. Descargando v3.1...")
    try:
        url = "https://github.com/Genymobile/scrcpy/releases/download/v3.1/scrcpy-linux-x86_64-v3.1.tar.gz"
        tar_path = os.path.join(BASE_DIR, "scrcpy_download.tar.gz")
        urllib.request.urlretrieve(url, tar_path)
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=SCRCPY_DIR)
        os.remove(tar_path)
        return check_dependencies()
    except Exception as e:
        print(f"{Fore.RED}[✘] Error descarga: {e}")
        return False

# --- NUEVA FUNCIÓN: SELECTOR INTELIGENTE DE DISPOSITIVO ---
def obtener_serial_prioritario():
    """
    Si hay USB y WiFi, devuelve el serial del USB.
    Si solo hay uno, devuelve ese.
    """
    try:
        res = subprocess.run("adb devices", shell=True, capture_output=True, text=True)
        lines = res.stdout.strip().split('\n')[1:] # Saltamos la cabecera "List of devices..."
        
        usb_serial = None
        wifi_serial = None
        
        for line in lines:
            if "device" in line and not "offline" in line:
                parts = line.split()
                if not parts: continue
                serial = parts[0]
                
                # Detectamos si es IP (WiFi) o Serial (USB)
                if "." in serial and ":" in serial: # Es una IP ej 192.168.1.35:5555
                    wifi_serial = serial
                else:
                    usb_serial = serial
        
        # PRIORIDAD: USB > WIFI
        if usb_serial: return usb_serial
        if wifi_serial: return wifi_serial
        return None
        
    except: return None

def get_device_info(serial=None):
    cmd = "adb "
    if serial: cmd += f"-s {serial} "
    cmd += "shell getprop ro.product.model"
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=2)
        return res.stdout.strip() if res.stdout.strip() else "..."
    except: return "Error ADB"

def get_best_encoder(serial=None):
    cmd = f"{SCRCPY_EXE} "
    if serial: cmd += f"-s {serial} "
    cmd += "--list-encoders"
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        if "OMX.qcom.video.encoder.avc" in res.stdout:
            return "OMX.qcom.video.encoder.avc"
        return "c2.android.avc.encoder"
    except: return "c2.android.avc.encoder"

def get_camera_ids(serial=None):
    cmd = f"{SCRCPY_EXE} "
    if serial: cmd += f"-s {serial} "
    cmd += "--list-cameras"
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        ids = []
        for line in (res.stdout + res.stderr).split('\n'):
            match = re.search(r'camera-id=(\d+)', line)
            if match:
                ids.append(match.group(1))
        return sorted(list(set(ids))) if ids else ["0", "1"]
    except: return ["0", "1"]

def setup_v4l2(node=10):
    os.system("sudo modprobe -r v4l2loopback 2>/dev/null")
    os.system(f"sudo modprobe v4l2loopback card_label='Webcam-Pro' exclusive_caps=1 video_nr={node}")
    return os.path.exists(f"/dev/video{node}")

def conectar_inalambrico():
    try:
        # Obtenemos IP (asumiendo que hay un USB conectado para el setup inicial)
        res = subprocess.run("adb shell ip -f inet addr show wlan0", shell=True, capture_output=True, text=True)
        match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', res.stdout)
        if not match: return False, "No IP (Activá WiFi)"
        ip = match.group(1)
        subprocess.run("adb tcpip 5555", shell=True, timeout=5)
        res = subprocess.run(f"adb connect {ip}:5555", shell=True, capture_output=True, text=True)
        if "connected" in res.stdout: return True, ip
        return False, "Error ADB"
    except Exception as e: return False, str(e)

# --- INTERFAZ GRÁFICA ---

class WebcamApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Scrcpy Webcam Ultimate")
        self.geometry("420x780")
        ctk.set_appearance_mode("dark")
        
        self.lang = "es"
        self.process = None
        
        # 1. Determinamos qué dispositivo usar al inicio
        self.target_serial = obtener_serial_prioritario()
        
        # 2. Cargamos datos usando ese serial específico
        self.modelo = get_device_info(self.target_serial)
        self.encoder = get_best_encoder(self.target_serial)
        self.raw_camera_ids = get_camera_ids(self.target_serial)

        # Header
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=10, pady=5)
        self.lang_opt = ctk.CTkOptionMenu(self.top_frame, values=["🇪🇸 ES", "🇺🇸 EN"], width=80, command=self.cambiar_idioma)
        self.lang_opt.pack(side="right")
        
        self.lbl_title = ctk.CTkLabel(self, text=TEXTOS[self.lang]["title"], font=("Roboto", 22, "bold"))
        self.lbl_title.pack(pady=(5, 15))

        # Status
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(fill="x", padx=25)
        self.lbl_model = ctk.CTkLabel(self.status_frame, text=f"📱 {self.modelo}", text_color="#3498db", font=("Arial", 14, "bold"))
        self.lbl_model.pack(side="left")
        self.btn_wifi = ctk.CTkButton(self.status_frame, text=TEXTOS[self.lang]["wifi_btn"], width=80, fg_color="#8e44ad", command=self.activar_wifi)
        self.btn_wifi.pack(side="right")

        # Controles
        self.lbl_lens = ctk.CTkLabel(self, text=TEXTOS[self.lang]["lens"])
        self.lbl_lens.pack(pady=(20, 5))
        
        self.cam_opt = ctk.CTkOptionMenu(self, values=[]) 
        self.cam_opt.pack(pady=5)
        
        self.lbl_res = ctk.CTkLabel(self, text=TEXTOS[self.lang]["res"])
        self.lbl_res.pack(pady=(15, 5))
        self.res_opt = ctk.CTkSegmentedButton(self, values=["720p", "1080p"], command=self.ajustar_bitrate)
        self.res_opt.set("720p")
        self.res_opt.pack(pady=5)
        
        self.lbl_bitrate_title = ctk.CTkLabel(self, text=TEXTOS[self.lang]["bitrate"])
        self.lbl_bitrate_title.pack(pady=(15, 5))
        self.lbl_bitrate_val = ctk.CTkLabel(self, text="8 Mbps")
        self.lbl_bitrate_val.pack()
        self.bit_slider = ctk.CTkSlider(self, from_=2, to=16, number_of_steps=14, command=lambda v: self.lbl_bitrate_val.configure(text=f"{int(v)} Mbps"))
        self.bit_slider.set(8)
        self.bit_slider.pack(pady=5)

        # Opciones
        self.opts_frame = ctk.CTkFrame(self)
        self.opts_frame.pack(pady=20, padx=20, fill="x")
        
        self.mirror_sw = ctk.CTkSwitch(self.opts_frame, text=TEXTOS[self.lang]["mirror"], onvalue=True, offvalue=False)
        self.mirror_sw.pack(pady=10)
        
        self.preview_sw = ctk.CTkSwitch(self.opts_frame, text=TEXTOS[self.lang]["preview"], onvalue=True, offvalue=False)
        self.preview_sw.pack(pady=10)

        # Botón
        self.btn = ctk.CTkButton(self, text=TEXTOS[self.lang]["start"], fg_color="#2ecc71", font=("Roboto", 14, "bold"), height=45, command=self.toggle_camara)
        self.btn.pack(pady=30, padx=20, fill="x")
        
        self.status = ctk.CTkLabel(self, text=TEXTOS[self.lang]["ready"], text_color="gray")
        self.status.pack(side="bottom", pady=10)
        
        self.actualizar_textos_camaras()

    def actualizar_textos_camaras(self):
        opciones = []
        t = TEXTOS[self.lang]
        for cid in self.raw_camera_ids:
            label = f"ID {cid} "
            if cid == "0": label += f"({t['cam_rear']})"
            elif cid == "1": label += f"({t['cam_front']})"
            else: label += f"({t['cam_aux']})"
            opciones.append(label)
        self.cam_opt.configure(values=opciones)
        if opciones: self.cam_opt.set(opciones[0])

    def cambiar_idioma(self, value):
        self.lang = "es" if "ES" in value else "en"
        t = TEXTOS[self.lang]
        self.lbl_title.configure(text=t["title"])
        self.btn_wifi.configure(text=t["wifi_btn"])
        self.lbl_lens.configure(text=t["lens"])
        self.lbl_res.configure(text=t["res"])
        self.lbl_bitrate_title.configure(text=t["bitrate"])
        self.mirror_sw.configure(text=t["mirror"])
        self.preview_sw.configure(text=t["preview"])
        self.actualizar_textos_camaras()
        if self.process:
            self.btn.configure(text=t["stop"])
            self.status.configure(text=t["live"])
        else:
            self.btn.configure(text=t["start"])
            self.status.configure(text=t["ready"])

    def ajustar_bitrate(self, value):
        if value == "1080p":
            self.bit_slider.set(5)
            self.lbl_bitrate_val.configure(text="5 Mbps (Rec)")
        else:
            self.bit_slider.set(8)
            self.lbl_bitrate_val.configure(text="8 Mbps")

    def activar_wifi(self):
        self.status.configure(text=TEXTOS[self.lang]["connecting"], text_color="yellow")
        def tarea():
            ok, msg = conectar_inalambrico()
            if ok:
                self.lbl_model.configure(text=f"📡 WiFi: {msg}")
                self.btn_wifi.configure(state="disabled", text="OK")
                self.status.configure(text=TEXTOS[self.lang]["wifi_success"], text_color="green")
            else:
                self.status.configure(text=f"{TEXTOS[self.lang]['wifi_fail']} {msg}", text_color="red")
        threading.Thread(target=tarea, daemon=True).start()

    def toggle_camara(self):
        t = TEXTOS[self.lang]
        if self.btn.cget("text") in [TEXTOS["es"]["start"], TEXTOS["en"]["start"]]:
            # REFRESCAMOS EL DISPOSITIVO OBJETIVO AL INICIAR
            # Esto es vital: si desconectaste el USB justo antes de iniciar, 
            # ahora detectará el WiFi automáticamente.
            self.target_serial = obtener_serial_prioritario()
            
            if not self.target_serial:
                self.status.configure(text="Error: No se detectó dispositivo", text_color="red")
                return

            self.thread = threading.Thread(target=self.lanzar_worker, daemon=True)
            self.thread.start()
            self.btn.configure(text=t["stop"], fg_color="#e74c3c")
            self.status.configure(text=t["live"], text_color="#e74c3c")
        else:
            self.detener()

    def lanzar_worker(self):
        try: cam_id = re.search(r'ID (\d+)', self.cam_opt.get()).group(1)
        except: cam_id = "0"
        
        res = "1920x1080" if self.res_opt.get() == "1080p" else "1280x720"
        bit = int(self.bit_slider.get())
        
        if setup_v4l2(10):
            cmd = [SCRCPY_EXE]
            
            # --- AGREGADO: SELECCIÓN DE SERIAL ---
            if self.target_serial:
                cmd.extend(["-s", self.target_serial])
            # -------------------------------------

            cmd.extend([
                "--video-source=camera", 
                f"--camera-id={cam_id}", f"--camera-size={res}", 
                f"--video-encoder={self.encoder}", f"--video-bit-rate={bit}M", 
                "--v4l2-sink=/dev/video10", "--no-audio", 
                "--video-buffer=0"
            ])
            
            if self.mirror_sw.get(): cmd.append("--orientation=flip0")
            if not self.preview_sw.get(): cmd.append("--no-video-playback")
            
            try:
                self.process = subprocess.Popen(cmd)
                self.process.wait()
            except Exception as e: print(f"Error: {e}")
            finally:
                t = TEXTOS[self.lang]
                self.btn.configure(text=t["start"], fg_color="#2ecc71")
                self.status.configure(text=t["finished"], text_color="gray")

    def detener(self):
        if self.process:
            self.process.terminate()
            self.process = None
        os.system("sudo modprobe -r v4l2loopback 2>/dev/null")

if __name__ == "__main__":
    print(f"{Fore.MAGENTA}=== Scrcpy Webcam Ultimate ===")
    if instalador_automatico() and check_dependencies():
        app = WebcamApp()
        app.mainloop()
    else:
        print(f"{Fore.RED}Error al iniciar.")