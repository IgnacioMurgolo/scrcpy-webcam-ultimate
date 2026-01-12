import customtkinter as ctk
import sys, subprocess, os, shutil, threading, re, urllib.request, tarfile, time
from colorama import Fore, init

init(autoreset=True)

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRCPY_DIR = os.path.join(BASE_DIR, "scrcpy-bin")
SCRCPY_EXE = None

POSIBLES_RUTAS = [
    os.path.join(SCRCPY_DIR, "scrcpy-linux-x86_64-v3.1", "scrcpy"),
    os.path.join(SCRCPY_DIR, "scrcpy")
]

TEXTOS = {
    "es": {
        "title": "Webcam Control", "wifi_btn": "🔗 WiFi",
        "lens": "Cámara", "res": "Resolución", 
        "mirror": "Modo Espejo", "audio": "Transmitir Audio",
        "preview": "Previsualizar", "start": "INICIAR TRANSMISIÓN",
        "stop": "DETENER", "ready": "Sistema Listo",
        "connecting": "Conectando...", "live": "🔴 EN EL AIRE",
        "wifi_success": "Conectado", "wifi_fail": "Error",
        "finished": "Finalizado", 
        "cam_rear": "Trasera (Principal)", "cam_front": "Frontal (Selfie)", "cam_aux": "Aux",
        "mode_usb": "🔌 USB", "mode_wifi": "📡 WIFI",
        "sect_video": "CONFIGURACIÓN DE VIDEO", "sect_opts": "OPCIONES",
        "no_cams": "Sin cámaras detectadas"
    },
    "en": {
        "title": "Webcam Control", "wifi_btn": "🔗 WiFi",
        "lens": "Camera", "res": "Resolution", 
        "mirror": "Mirror Mode", "audio": "Stream Audio",
        "preview": "Preview", "start": "START STREAM",
        "stop": "STOP", "ready": "System Ready",
        "connecting": "Connecting...", "live": "🔴 LIVE ON AIR",
        "wifi_success": "Connected", "wifi_fail": "Error",
        "finished": "Ended", 
        "cam_rear": "Back (Main)", "cam_front": "Front (Selfie)", "cam_aux": "Aux",
        "mode_usb": "🔌 USB", "mode_wifi": "📡 WIFI",
        "sect_video": "VIDEO SETTINGS", "sect_opts": "OPTIONS",
        "no_cams": "No cameras found"
    }
}

# --- LÓGICA DE SISTEMA ---

def buscar_scrcpy():
    global SCRCPY_EXE
    for ruta in POSIBLES_RUTAS:
        if ruta and os.path.exists(ruta):
            if os.access(ruta, os.X_OK):
                SCRCPY_EXE = ruta; return True
    return False

def instalador_automatico():
    if shutil.which("adb") is not None and buscar_scrcpy(): return True
    try:
        url = "https://github.com/Genymobile/scrcpy/releases/download/v3.1/scrcpy-linux-x86_64-v3.1.tar.gz"
        tar_path = os.path.join(BASE_DIR, "scrcpy_download.tar.gz")
        urllib.request.urlretrieve(url, tar_path)
        os.makedirs(SCRCPY_DIR, exist_ok=True)
        with tarfile.open(tar_path, "r:gz") as tar: tar.extractall(path=SCRCPY_DIR)
        os.remove(tar_path); return buscar_scrcpy()
    except: return False

def obtener_serial_prioritario():
    try:
        res = subprocess.run("adb devices", shell=True, capture_output=True, text=True)
        lines = res.stdout.strip().split('\n')[1:]
        usb, wifi = None, None
        for line in lines:
            if "device" in line and not "offline" in line:
                s = line.split()[0]
                if "." in s: wifi = s
                else: usb = s
        return usb if usb else wifi
    except: return None

def get_camera_ids(serial=None):
    cmd = f"{SCRCPY_EXE} {'-s ' + serial if serial else ''} --list-cameras"
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        ids = re.findall(r'camera-id=(\d+)', res.stdout + res.stderr)
        return sorted(list(set(ids))) if ids else []
    except: return []

def conectar_inalambrico():
    try:
        subprocess.run("adb disconnect", shell=True)
        time.sleep(1)
        res = subprocess.run("adb shell ip -f inet addr show wlan0", shell=True, capture_output=True, text=True)
        match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', res.stdout)
        if not match:
            res = subprocess.run("adb shell ip route", shell=True, capture_output=True, text=True)
            match = re.search(r'src (\d+\.\d+\.\d+\.\d+)', res.stdout)
        if not match: return False, "No IP"
        ip = match.group(1)
        subprocess.run("adb tcpip 5555", shell=True, timeout=5)
        time.sleep(2)
        res = subprocess.run(f"adb connect {ip}:5555", shell=True, capture_output=True, text=True)
        if "connected" in res.stdout: return True, f"{ip}:5555"
        return False, "Reintentar"
    except Exception as e: return False, str(e)

def setup_v4l2(node=10):
    os.system("pkill -9 scrcpy 2>/dev/null")
    ret = os.system(f"sudo modprobe -r v4l2loopback && sudo modprobe v4l2loopback card_label='Webcam-Pro' exclusive_caps=1 video_nr={node}")
    if ret != 0:
        cmd = f"modprobe -r v4l2loopback; modprobe v4l2loopback card_label='Webcam-Pro' exclusive_caps=1 video_nr={node}"
        os.system(f"pkexec sh -c \"{cmd}\"")
    return os.path.exists(f"/dev/video{node}")

def crear_lanzador_linux():
    if os.name != 'posix': return
    repo_path = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(repo_path, "venv", "bin", "python3")
    if not os.path.exists(venv_python): venv_python = "python3"
    contenido = f"""[Desktop Entry]
Name=Webcam Ultimate
Exec={venv_python} {os.path.join(repo_path, "main.py")}
Path={repo_path}
Icon=camera-web
Terminal=false
Type=Application
Categories=Video;AudioVideo;
"""
    p = os.path.expanduser("~/.local/share/applications/Webcam-Ultimate.desktop")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f: f.write(contenido)
    os.chmod(p, 0o755)

# --- INTERFAZ ---
class WebcamApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Scrcpy Webcam")
        self.geometry("400x720")
        ctk.set_appearance_mode("dark")
        self.lang = "es"
        self.process = None
        
        self.target_serial = obtener_serial_prioritario()
        self.raw_camera_ids = get_camera_ids(self.target_serial)
        
        if not self.raw_camera_ids:
             self.raw_camera_ids = ["0", "1"] 

        # HEADER
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=15, pady=(15, 5))
        self.lbl_title = ctk.CTkLabel(self.header, text=TEXTOS[self.lang]["title"], font=("Roboto", 18, "bold"))
        self.lbl_title.pack(side="left")
        self.lang_opt = ctk.CTkSegmentedButton(self.header, values=["ES", "EN"], width=60, height=24, command=self.cambiar_idioma)
        self.lang_opt.set("ES"); self.lang_opt.pack(side="right")

        # STATUS BADGE
        self.status_card = ctk.CTkFrame(self, fg_color="#1f1f1f", corner_radius=8, height=40)
        self.status_card.pack(fill="x", padx=15, pady=5)
        self.status_card.grid_columnconfigure(1, weight=1)
        self.lbl_conn_type = ctk.CTkLabel(self.status_card, text="...", font=("Arial", 12, "bold"))
        self.lbl_conn_type.grid(row=0, column=0, padx=15, pady=8, sticky="w")
        self.btn_wifi = ctk.CTkButton(self.status_card, text=TEXTOS[self.lang]["wifi_btn"], width=80, height=24, fg_color="#444444", hover_color="#555555", command=self.activar_wifi)
        self.btn_wifi.grid(row=0, column=2, padx=10, pady=8, sticky="e")

        # VIDEO SETTINGS
        self.sect_video = ctk.CTkFrame(self)
        self.sect_video.pack(pady=5, padx=15, fill="x")
        
        # AQUI ESTÁ EL ARREGLO: Guardamos la etiqueta en self.lbl_vid_title
        self.lbl_vid_title = ctk.CTkLabel(self.sect_video, text=TEXTOS[self.lang]["sect_video"], font=("Arial", 10, "bold"), text_color="gray")
        self.lbl_vid_title.pack(pady=(5,0), anchor="w", padx=10)

        self.cam_opt = ctk.CTkOptionMenu(self.sect_video, values=[], height=28)
        self.cam_opt.pack(pady=5, padx=10, fill="x")
        
        self.res_opt = ctk.CTkSegmentedButton(self.sect_video, values=["720p", "1080p"], height=28, command=self.preset_resolucion)
        self.res_opt.set("720p")
        self.res_opt.pack(pady=5, padx=10, fill="x")

        self.lbl_bit_val = ctk.CTkLabel(self.sect_video, text="5 Mbps (Rec)", font=("Arial", 11))
        self.lbl_bit_val.pack(pady=(5, 0))
        self.bit_slider = ctk.CTkSlider(self.sect_video, from_=2, to=16, number_of_steps=14, height=16, command=self.actualizar_bitrate_texto)
        self.bit_slider.set(5)
        self.bit_slider.pack(pady=(0, 10), padx=10, fill="x")

        # OPCIONES
        self.sect_opts = ctk.CTkFrame(self)
        self.sect_opts.pack(pady=5, padx=15, fill="x")
        
        # AQUI TAMBIÉN: Guardamos la etiqueta en self.lbl_opts_title
        self.lbl_opts_title = ctk.CTkLabel(self.sect_opts, text=TEXTOS[self.lang]["sect_opts"], font=("Arial", 10, "bold"), text_color="gray")
        self.lbl_opts_title.pack(pady=(5,0), anchor="w", padx=10)

        self.audio_sw = ctk.CTkSwitch(self.sect_opts, text=TEXTOS[self.lang]["audio"], font=("Arial", 12))
        self.audio_sw.pack(pady=5, padx=10, anchor="w")
        self.mirror_sw = ctk.CTkSwitch(self.sect_opts, text=TEXTOS[self.lang]["mirror"], font=("Arial", 12))
        self.mirror_sw.pack(pady=5, padx=10, anchor="w")
        self.preview_sw = ctk.CTkSwitch(self.sect_opts, text=TEXTOS[self.lang]["preview"], font=("Arial", 12))
        self.preview_sw.select(); self.preview_sw.pack(pady=(5, 10), padx=10, anchor="w")

        # FOOTER
        self.btn = ctk.CTkButton(self, text=TEXTOS[self.lang]["start"], fg_color="#2ecc71", height=38, font=("Roboto", 13, "bold"), command=self.toggle)
        self.btn.pack(pady=15, padx=15, fill="x")
        self.status = ctk.CTkLabel(self, text=TEXTOS[self.lang]["ready"], text_color="gray", font=("Arial", 10))
        self.status.pack(side="bottom", pady=5)
        
        self.actualizar_tipo_conexion()
        self.actualizar_textos()

    def actualizar_bitrate_texto(self, val):
        self.lbl_bit_val.configure(text=f"{int(val)} Mbps")

    def preset_resolucion(self, res):
        if res == "720p":
            self.bit_slider.set(5)
            self.lbl_bit_val.configure(text="5 Mbps (Rec)")
        else:
            self.bit_slider.set(8)
            self.lbl_bit_val.configure(text="8 Mbps (Rec)")

    def actualizar_tipo_conexion(self):
        t = TEXTOS[self.lang]
        if not self.target_serial:
            self.lbl_conn_type.configure(text="---", text_color="gray")
            self.status_card.configure(fg_color="#1f1f1f")
            return
        if "." in self.target_serial:
            self.lbl_conn_type.configure(text=t["mode_wifi"], text_color="#ffffff")
            self.status_card.configure(fg_color="#d35400")
        else:
            self.lbl_conn_type.configure(text=t["mode_usb"], text_color="#ffffff")
            self.status_card.configure(fg_color="#2980b9")

    def actualizar_textos(self):
        t = TEXTOS[self.lang]
        self.lbl_title.configure(text=t["title"])
        self.btn_wifi.configure(text=t["wifi_btn"])
        
        # ACTUALIZAMOS LOS TÍTULOS DE SECCIÓN
        self.lbl_vid_title.configure(text=t["sect_video"])
        self.lbl_opts_title.configure(text=t["sect_opts"])

        self.audio_sw.configure(text=t["audio"]); self.mirror_sw.configure(text=t["mirror"])
        self.preview_sw.configure(text=t["preview"])
        self.btn.configure(text=t["start"] if not self.process else t["stop"])
        
        vals = []
        for cid in self.raw_camera_ids:
            name = f"ID {cid}: "
            if cid == "0": name += t["cam_rear"]
            elif cid == "1": name += t["cam_front"]
            else: name += t["cam_aux"]
            vals.append(name)
        
        if not vals: vals = [t["no_cams"]]
        
        self.cam_opt.configure(values=vals)
        current = self.cam_opt.get()
        if current == "CTkOptionMenu" or current not in vals:
             self.cam_opt.set(vals[0])
        
        self.actualizar_tipo_conexion()

    def cambiar_idioma(self, v):
        self.lang = "es" if v == "ES" else "en"
        self.actualizar_textos()

    def activar_wifi(self):
        self.status.configure(text=TEXTOS[self.lang]["connecting"], text_color="yellow")
        def tarea():
            ok, msg = conectar_inalambrico()
            if ok:
                self.target_serial = msg
                self.actualizar_tipo_conexion()
            self.status.configure(text=f"Info: {msg}", text_color="green" if ok else "red")
        threading.Thread(target=tarea, daemon=True).start()

    def toggle(self):
        if not self.process:
            nuevo = obtener_serial_prioritario()
            if nuevo and not ('.' in nuevo):
                if self.target_serial != nuevo:
                    subprocess.run("adb disconnect", shell=True)
                    self.target_serial = nuevo
                    self.actualizar_tipo_conexion()

            if not self.target_serial:
                self.status.configure(text="Error: No Device", text_color="red")
                return
            
            os.system("pkill -9 scrcpy 2>/dev/null")
            threading.Thread(target=self.run_scrcpy, daemon=True).start()
        else:
            if self.process: self.process.terminate()
            os.system("pkill -9 scrcpy 2>/dev/null")

    def run_scrcpy(self):
        try: cid = re.search(r'ID (\d+)', self.cam_opt.get()).group(1)
        except: cid = "0"
        
        setup_v4l2(10)
        
        cmd = [SCRCPY_EXE]
        if self.target_serial: cmd.extend(["-s", self.target_serial])
        
        cmd.extend([
            "--video-source=camera", f"--camera-id={cid}", 
            f"--camera-size={'1920x1080' if self.res_opt.get() == '1080p' else '1280x720'}", 
            f"--video-bit-rate={int(self.bit_slider.get())}M", 
            "--v4l2-sink=/dev/video10", "--video-buffer=0"
        ])
        
        if not self.audio_sw.get(): cmd.append("--no-audio")
        else: cmd.extend(["--audio-bit-rate=64K"])

        if self.mirror_sw.get(): cmd.append("--orientation=flip0")
        if not self.preview_sw.get(): cmd.append("--no-video-playback")
        
        self.btn.configure(text=TEXTOS[self.lang]["stop"], fg_color="#e74c3c")
        self.status.configure(text=TEXTOS[self.lang]["live"], text_color="#e74c3c")
        
        self.process = subprocess.Popen(cmd)
        self.process.wait()
        
        self.btn.configure(text=TEXTOS[self.lang]["start"], fg_color="#2ecc71")
        self.status.configure(text=TEXTOS[self.lang]["finished"], text_color="gray")
        self.process = None

if __name__ == "__main__":
    if instalador_automatico():
        crear_lanzador_linux()
        WebcamApp().mainloop()