import customtkinter as ctk
import sys, subprocess, os, shutil, threading, re, urllib.request, tarfile, time, json
from colorama import Fore, init

init(autoreset=True)

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRCPY_BIN_DIR = os.path.join(BASE_DIR, "scrcpy-bin")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
SCRCPY_EXE = None

# Priority: Local v3.1 > Local > System
POSSIBLE_PATHS = [
    os.path.join(SCRCPY_BIN_DIR, "scrcpy-linux-x86_64-v3.1", "scrcpy"),
    os.path.join(SCRCPY_BIN_DIR, "scrcpy"),
    shutil.which("scrcpy")
]

DEFAULT_CONFIG = {
    "lang": "es",
    "res": "720p",
    "bitrate": 5,
    "audio": False,
    "mirror": False,
    "preview": True
}

# UI Strings Dictionary
LOCALIZATION = {
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
        "no_cams": "Sin cámaras detectadas",
        "batt": "Batería"
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
        "no_cams": "No cameras found",
        "batt": "Battery"
    }
}

# --- BACKEND LOGIC ---

def find_scrcpy_executable():
    global SCRCPY_EXE
    for path in POSSIBLE_PATHS:
        if path and os.path.exists(path):
            if os.access(path, os.X_OK):
                SCRCPY_EXE = path
                return True
    return False

def automatic_setup():
    """Checks dependencies and downloads scrcpy if missing."""
    if shutil.which("adb") is not None and find_scrcpy_executable():
        return True
    
    print(f"{Fore.YELLOW}[Setup] Downloading Scrcpy v3.1...")
    try:
        url = "https://github.com/Genymobile/scrcpy/releases/download/v3.1/scrcpy-linux-x86_64-v3.1.tar.gz"
        tar_path = os.path.join(BASE_DIR, "scrcpy_download.tar.gz")
        urllib.request.urlretrieve(url, tar_path)
        
        os.makedirs(SCRCPY_BIN_DIR, exist_ok=True)
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=SCRCPY_BIN_DIR)
            
        os.remove(tar_path)
        return find_scrcpy_executable()
    except Exception as e:
        print(f"{Fore.RED}[Setup] Error: {e}")
        return False

def get_prioritized_serial():
    """Returns USB serial if available, otherwise WiFi IP."""
    try:
        res = subprocess.run("adb devices", shell=True, capture_output=True, text=True)
        lines = res.stdout.strip().split('\n')[1:]
        usb_serial, wifi_serial = None, None
        
        for line in lines:
            if "device" in line and not "offline" in line:
                s = line.split()[0]
                if "." in s: wifi_serial = s
                else: usb_serial = s
                
        return usb_serial if usb_serial else wifi_serial
    except: return None

def get_camera_ids(serial=None):
    """Parses available camera IDs from scrcpy."""
    cmd = f"{SCRCPY_EXE} {'-s ' + serial if serial else ''} --list-cameras"
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        ids = re.findall(r'camera-id=(\d+)', res.stdout + res.stderr)
        return sorted(list(set(ids))) if ids else []
    except: return []

def get_battery_level(serial=None):
    """Fetches battery level via ADB dumpsys."""
    cmd = f"adb {'-s ' + serial if serial else ''} shell dumpsys battery"
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        level = re.search(r'level: (\d+)', res.stdout)
        return int(level.group(1)) if level else 0
    except: return 0

def connect_wireless():
    """Robust connection logic for Android/ADB."""
    try:
        # 1. Clear previous sessions
        subprocess.run("adb disconnect", shell=True)
        time.sleep(1)
        
        # 2. Find IP (Specific to wlan0 interface)
        res = subprocess.run("adb shell ip -f inet addr show wlan0", shell=True, capture_output=True, text=True)
        match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', res.stdout)
        
        # Fallback to generic route
        if not match:
            res = subprocess.run("adb shell ip route", shell=True, capture_output=True, text=True)
            match = re.search(r'src (\d+\.\d+\.\d+\.\d+)', res.stdout)

        if not match: return False, "No IP"
        ip = match.group(1)
        
        # 3. Enable TCP/IP
        subprocess.run("adb tcpip 5555", shell=True, timeout=5)
        time.sleep(2)
        
        # 4. Connect
        res = subprocess.run(f"adb connect {ip}:5555", shell=True, capture_output=True, text=True)
        if "connected" in res.stdout: return True, f"{ip}:5555"
        return False, "Retry Error"
    except Exception as e: return False, str(e)

def reset_v4l2_driver(node=10):
    """Resets the v4l2loopback kernel module to ensure detection."""
    os.system("pkill -9 scrcpy 2>/dev/null")
    
    # Try sudo-less execution (if configured in sudoers)
    ret = os.system(f"sudo modprobe -r v4l2loopback && sudo modprobe v4l2loopback card_label='Webcam-Pro' exclusive_caps=1 video_nr={node}")
    
    # Fallback to graphical authentication (pkexec)
    if ret != 0:
        cmd = f"modprobe -r v4l2loopback; modprobe v4l2loopback card_label='Webcam-Pro' exclusive_caps=1 video_nr={node}"
        os.system(f"pkexec sh -c \"{cmd}\"")
        
    return os.path.exists(f"/dev/video{node}")

def create_linux_launcher():
    if os.name != 'posix': return
    repo_path = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(repo_path, "venv", "bin", "python3")
    if not os.path.exists(venv_python): venv_python = "python3"
    
    content = f"""[Desktop Entry]
Name=Webcam Ultimate
Exec={venv_python} {os.path.join(repo_path, "main.py")}
Path={repo_path}
Icon=camera-web
Terminal=false
Type=Application
Categories=Video;AudioVideo;
"""
    desktop_file = os.path.expanduser("~/.local/share/applications/Webcam-Ultimate.desktop")
    os.makedirs(os.path.dirname(desktop_file), exist_ok=True)
    with open(desktop_file, "w") as f: f.write(content)
    os.chmod(desktop_file, 0o755)

# --- GUI ---
class WebcamApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Scrcpy Webcam")
        self.geometry("400x750")
        ctk.set_appearance_mode("dark")
        self.process = None
        self.is_running = True # For battery thread loop
        
        # Load Config
        self.config = self.load_config()
        self.lang = self.config["lang"]
        
        self.target_serial = get_prioritized_serial()
        self.raw_camera_ids = get_camera_ids(self.target_serial)
        if not self.raw_camera_ids: self.raw_camera_ids = ["0", "1"] 

        # --- HEADER ---
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=15, pady=(15, 5))
        self.lbl_title = ctk.CTkLabel(self.header, text=LOCALIZATION[self.lang]["title"], font=("Roboto", 18, "bold"))
        self.lbl_title.pack(side="left")
        self.lang_selector = ctk.CTkSegmentedButton(self.header, values=["ES", "EN"], width=60, height=24, command=self.change_language)
        self.lang_selector.set("ES" if self.lang == "es" else "EN")
        self.lang_selector.pack(side="right")

        # --- STATUS BADGE ---
        self.status_card = ctk.CTkFrame(self, fg_color="#1f1f1f", corner_radius=8, height=40)
        self.status_card.pack(fill="x", padx=15, pady=5)
        self.status_card.grid_columnconfigure(1, weight=1)
        
        self.lbl_conn_type = ctk.CTkLabel(self.status_card, text="...", font=("Arial", 11, "bold"))
        self.lbl_conn_type.grid(row=0, column=0, padx=10, pady=8, sticky="w")
        
        self.lbl_battery = ctk.CTkLabel(self.status_card, text="🔋 --%", font=("Arial", 12))
        self.lbl_battery.grid(row=0, column=1, pady=8)

        self.btn_wifi = ctk.CTkButton(self.status_card, text=LOCALIZATION[self.lang]["wifi_btn"], width=80, height=24, fg_color="#444444", hover_color="#555555", command=self.enable_wifi_mode)
        self.btn_wifi.grid(row=0, column=2, padx=10, pady=8, sticky="e")

        # --- VIDEO SETTINGS ---
        self.sect_video = ctk.CTkFrame(self)
        self.sect_video.pack(pady=5, padx=15, fill="x")
        self.lbl_vid_title = ctk.CTkLabel(self.sect_video, text=LOCALIZATION[self.lang]["sect_video"], font=("Arial", 10, "bold"), text_color="gray")
        self.lbl_vid_title.pack(pady=(5,0), anchor="w", padx=10)

        self.cam_opt = ctk.CTkOptionMenu(self.sect_video, values=[], height=28)
        self.cam_opt.pack(pady=5, padx=10, fill="x")
        
        self.res_opt = ctk.CTkSegmentedButton(self.sect_video, values=["720p", "1080p"], height=28, command=self.preset_resolution)
        self.res_opt.set(self.config["res"])
        self.res_opt.pack(pady=5, padx=10, fill="x")

        self.lbl_bit_val = ctk.CTkLabel(self.sect_video, text="5 Mbps (Rec)", font=("Arial", 11))
        self.lbl_bit_val.pack(pady=(5, 0))
        self.bit_slider = ctk.CTkSlider(self.sect_video, from_=2, to=16, number_of_steps=14, height=16, command=self.update_bitrate_label)
        self.bit_slider.set(self.config["bitrate"])
        self.bit_slider.pack(pady=(0, 10), padx=10, fill="x")

        # --- OPTIONS ---
        self.sect_opts = ctk.CTkFrame(self)
        self.sect_opts.pack(pady=5, padx=15, fill="x")
        self.lbl_opts_title = ctk.CTkLabel(self.sect_opts, text=LOCALIZATION[self.lang]["sect_opts"], font=("Arial", 10, "bold"), text_color="gray")
        self.lbl_opts_title.pack(pady=(5,0), anchor="w", padx=10)

        self.audio_sw = ctk.CTkSwitch(self.sect_opts, text=LOCALIZATION[self.lang]["audio"], font=("Arial", 12))
        if self.config["audio"]: self.audio_sw.select()
        self.audio_sw.pack(pady=5, padx=10, anchor="w")
        
        self.mirror_sw = ctk.CTkSwitch(self.sect_opts, text=LOCALIZATION[self.lang]["mirror"], font=("Arial", 12))
        if self.config["mirror"]: self.mirror_sw.select()
        self.mirror_sw.pack(pady=5, padx=10, anchor="w")
        
        self.preview_sw = ctk.CTkSwitch(self.sect_opts, text=LOCALIZATION[self.lang]["preview"], font=("Arial", 12))
        if self.config["preview"]: self.preview_sw.select()
        self.preview_sw.pack(pady=(5, 10), padx=10, anchor="w")

        # --- FOOTER ---
        self.btn_main = ctk.CTkButton(self, text=LOCALIZATION[self.lang]["start"], fg_color="#2ecc71", height=38, font=("Roboto", 13, "bold"), command=self.toggle_stream)
        self.btn_main.pack(pady=15, padx=15, fill="x")
        self.status = ctk.CTkLabel(self, text=LOCALIZATION[self.lang]["ready"], text_color="gray", font=("Arial", 10))
        self.status.pack(side="bottom", pady=5)
        
        # Init logic
        self.update_ui_text()
        self.update_bitrate_label(self.config["bitrate"])
        
        # Background threads
        threading.Thread(target=self.track_battery_level, daemon=True).start()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # --- PERSISTENCE ---
    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f: return json.load(f)
        except: pass
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        cfg = {
            "lang": self.lang,
            "res": self.res_opt.get(),
            "bitrate": int(self.bit_slider.get()),
            "audio": bool(self.audio_sw.get()),
            "mirror": bool(self.mirror_sw.get()),
            "preview": bool(self.preview_sw.get())
        }
        try:
            with open(CONFIG_FILE, "w") as f: json.dump(cfg, f)
        except: pass

    def on_close(self):
        self.is_running = False
        self.save_config()
        self.stop_process()
        self.destroy()

    # --- WORKERS ---
    def track_battery_level(self):
        while self.is_running:
            if self.target_serial:
                level = get_battery_level(self.target_serial)
                t = LOCALIZATION[self.lang]["batt"]
                color = "#2ecc71" if level > 20 else "#e74c3c"
                try: self.lbl_battery.configure(text=f"{t}: {level}%", text_color=color)
                except: break
            else:
                try: self.lbl_battery.configure(text="--", text_color="gray")
                except: break
            time.sleep(10)

    # --- UI ACTIONS ---
    def update_bitrate_label(self, val):
        self.lbl_bit_val.configure(text=f"{int(val)} Mbps")

    def preset_resolution(self, res):
        if res == "720p":
            self.bit_slider.set(5); self.lbl_bit_val.configure(text="5 Mbps (Rec)")
        else:
            self.bit_slider.set(8); self.lbl_bit_val.configure(text="8 Mbps (Rec)")

    def update_connection_badge(self):
        t = LOCALIZATION[self.lang]
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

    def update_ui_text(self):
        t = LOCALIZATION[self.lang]
        self.lbl_title.configure(text=t["title"])
        self.btn_wifi.configure(text=t["wifi_btn"])
        self.lbl_vid_title.configure(text=t["sect_video"])
       # self.lbl_battery.configure(text=t["batt"])
        self.lbl_opts_title.configure(text=t["sect_opts"])
        self.audio_sw.configure(text=t["audio"]); self.mirror_sw.configure(text=t["mirror"])
        self.preview_sw.configure(text=t["preview"])
        self.btn_main.configure(text=t["start"] if not self.process else t["stop"])
        
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
        
        self.update_connection_badge()

    def change_language(self, v):
        self.lang = "es" if v == "ES" else "en"
        self.update_ui_text()

    def enable_wifi_mode(self):
        self.status.configure(text=LOCALIZATION[self.lang]["connecting"], text_color="yellow")
        def task():
            ok, msg = connect_wireless()
            if ok:
                self.target_serial = msg
                self.update_connection_badge()
            self.status.configure(text=f"Info: {msg}", text_color="green" if ok else "red")
        threading.Thread(target=task, daemon=True).start()

    def toggle_stream(self):
        if not self.process:
            # Auto-switch to USB check
            new_dev = get_prioritized_serial()
            if new_dev and not ('.' in new_dev):
                if self.target_serial != new_dev:
                    subprocess.run("adb disconnect", shell=True)
                    self.target_serial = new_dev
                    self.update_connection_badge()

            if not self.target_serial:
                self.status.configure(text="Error: No Device", text_color="red")
                return
            
            os.system("pkill -9 scrcpy 2>/dev/null")
            threading.Thread(target=self.start_scrcpy_process, daemon=True).start()
        else:
            self.stop_process()

    def start_scrcpy_process(self):
        try: cid = re.search(r'ID (\d+)', self.cam_opt.get()).group(1)
        except: cid = "0"
        
        reset_v4l2_driver(10)
        
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
        
        t = LOCALIZATION[self.lang]
        self.btn_main.configure(text=t["stop"], fg_color="#e74c3c")
        self.status.configure(text=t["live"], text_color="#e74c3c")
        
        try:
            self.process = subprocess.Popen(cmd)
            self.process.wait()
        except: pass
        
        self.btn_main.configure(text=t["start"], fg_color="#2ecc71")
        self.status.configure(text=t["finished"], text_color="gray")
        self.process = None

    def stop_process(self):
        if self.process:
            self.process.terminate()
            self.process = None
        os.system("pkill -9 scrcpy 2>/dev/null")

if __name__ == "__main__":
    if automatic_setup():
        create_linux_launcher()
        WebcamApp().mainloop()