# Roblox Avatar Rotator
# Created by fowntain on all platforms (except twitter @fowntainwhat)
# Modified for MacOS (tested on Monterey) by dan

import requests
import time
import threading
import json
import os
import sys
import logging
import tkinter as tk
from tkinter import messagebox, Listbox, MULTIPLE, END
import subprocess
import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as item

# logging
LOG_FILE = "rotator_log.txt"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)

def log(msg, level="info"):
    print(msg) 
    if level == "info": logging.info(msg)
    elif level == "error": logging.error(msg)
    elif level == "warning": logging.warning(msg)

def open_logs():
    if not os.path.exists(LOG_FILE):
        log("Log file created.", "info")
    subprocess.run(["open", LOG_FILE])

# configs
CONFIG_FILE = "config.json"
APP_NAME = "RobloxAvatarRotator"

class ConfigManager:
    @staticmethod
    def load():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                log(f"Failed to load config: {e}", "error")
                return {}
        return {}

    @staticmethod
    def save(data):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f, indent=4)
            log("Configuration saved.", "info")
        except Exception as e:
            log(f"Failed to save config: {e}", "error")

    @staticmethod
    def get_startup_status():
        return False

    @staticmethod
    def toggle_startup(enable):
        if enable:
            log("Startup is not supported on macOS.", "warning")
# api handler
class RobloxAvatarManager:
    def __init__(self):
        self.session = requests.Session()
        self.avatar_type_map = {"R6": 1, "R15": 3}
        self.user_id = None

    def update_cookie(self, cookie):
        self.session.cookies['.ROBLOSECURITY'] = cookie
    
    def get_authenticated_user(self):
        """Fetches the user ID associated with the cookie."""
        try:
            res = self.session.get("https://users.roblox.com/v1/users/authenticated")
            if res.status_code == 200:
                data = res.json()
                self.user_id = data.get("id")
                return data
            else:
                log(f"Auth check failed: {res.status_code}", "error")
                return None
        except Exception as e:
            log(f"Auth check error: {e}", "error")
            return None

    def fetch_user_outfits(self):
        """Fetches all outfits for the authenticated user."""
        if not self.user_id:
            user = self.get_authenticated_user()
            if not user: return []

        outfits = []
        page = 1
        url = f"https://avatar.roblox.com/v2/avatar/users/{self.user_id}/outfits?page=1&itemsPerPage=50&isEditable=true"
        
        try:
            res = self.session.get(url)
            if res.status_code == 200:
                data = res.json()
                for item in data.get("data", []):
                    if item.get("outfitType") == "Avatar":
                        outfits.append({"id": item["id"], "name": item["name"]})
            else:
                log(f"Failed to fetch outfits: {res.status_code}", "error")
        except Exception as e:
            log(f"Error fetching outfits: {e}", "error")
        
        return outfits

    def _make_request(self, method, url, json_data=None):
        try:
            if method == "GET": 
                response = self.session.get(url)
            else: 
                response = self.session.post(url, json=json_data)

            if response.status_code == 403 and "x-csrf-token" in response.headers:
                log("CSRF Token expired. Refreshing...", "warning")
                self.session.headers["x-csrf-token"] = response.headers["x-csrf-token"]
                if method == "GET": 
                    response = self.session.get(url)
                else: 
                    response = self.session.post(url, json=json_data)
            
            if response.status_code not in [200, 201]:
                log(f"Request failed [{response.status_code}]: {url} - {response.text[:100]}", "error")
            
            return response
        except Exception as e:
            log(f"Connection Error: {e}", "error")
            return None

    def get_outfit_details(self, outfit_id):
        res = self._make_request("GET", f"https://avatar.roblox.com/v3/outfits/{outfit_id}/details")
        if res and res.status_code == 200:
            return res.json()
        log(f"Failed to fetch outfit details for ID: {outfit_id}", "error")
        return None

    def set_avatar_type(self, type_string):
        type_enum = self.avatar_type_map.get(type_string)
        if type_enum:
            res = self._make_request("POST", "https://avatar.roblox.com/v1/avatar/set-player-avatar-type", {"playerAvatarType": type_enum})
            if res and res.status_code == 200: log(f"Set Type: {type_string}", "info")

    def set_body_colors(self, colors):
        res = self._make_request("POST", "https://avatar.roblox.com/v2/avatar/set-body-colors", colors)
        if res and res.status_code == 200: log("Set Body Colors", "info")

    def set_wearing_assets(self, assets):
        clean_assets = []
        for asset in assets:
            new_asset = {"id": asset["id"]}
            if "meta" in asset:
                new_asset["meta"] = asset["meta"]
            clean_assets.append(new_asset)

        res = self._make_request("POST", "https://avatar.roblox.com/v2/avatar/set-wearing-assets", {"assets": clean_assets})
        
        if res and res.status_code == 200: 
            log(f"Equipped {len(clean_assets)} assets.", "info")
        else:
            log("Failed to equip assets.", "error")

# rotator logic
class AvatarRotator:
    def __init__(self):
        self.active = False
        self.running = True
        self.bot = RobloxAvatarManager()
        self.outfit_cache = {}
        self.outfit_ids = []
        self.outfit_names = []
        self.interval = 5
        
        cfg = ConfigManager.load()
        if "cookie" in cfg: self.bot.update_cookie(cfg["cookie"])
        if "outfits" in cfg: 
            raw_outfits = cfg["outfits"]
            if raw_outfits and isinstance(raw_outfits[0], dict):
                self.outfit_ids = [o["id"] for o in raw_outfits]
                self.outfit_names = [o["name"] for o in raw_outfits]
            else:
                self.outfit_ids = raw_outfits
                self.outfit_names = [str(i) for i in raw_outfits]

        if "interval" in cfg: self.interval = cfg["interval"]

        self.thread = threading.Thread(target=self.loop)
        self.thread.daemon = True
        self.thread.start()

        if cfg.get("cookie") and cfg.get("outfits"):
            self.start_rotation()
        else:
            self.send_toast("Setup Required", "Right-click tray -> Settings to configure.")

    def send_toast(self, title, msg):
        log(f"{title}: {msg}", "info")

    def start_rotation(self):
        cfg = ConfigManager.load()
        if not cfg.get("cookie") or not cfg.get("outfits"):
            self.send_toast("Cannot Start", "Check Settings.")
            return

        self.bot.update_cookie(cfg["cookie"])
        
        raw_outfits = cfg["outfits"]
        if raw_outfits and isinstance(raw_outfits[0], dict):
            self.outfit_ids = [o["id"] for o in raw_outfits]
            self.outfit_names = [o["name"] for o in raw_outfits]
        
        if "interval" in cfg: self.interval = max(1, int(cfg["interval"]))

        self.outfit_cache = {}
        log("Cache cleared. Fetching fresh outfit data...", "info")
        
        self.active = True
        self.send_toast("Started", f"Rotation active ({self.interval}s).")
        log("Rotation started.", "info")

        threading.Thread(target=self._cache_outfits).start()

    def _cache_outfits(self):
        for oid in self.outfit_ids:
            if not self.active: break 
            if oid not in self.outfit_cache:
                details = self.bot.get_outfit_details(oid)
                if details:
                    self.outfit_cache[oid] = details
                    log(f"Cached outfit details.", "info")
                time.sleep(1)

    def stop_rotation(self):
        self.active = False
        self.send_toast("Stopped", "Rotation paused.")
        log("Rotation stopped.", "info")

    def loop(self):
        outfit_index = 0
        while self.running:
            if self.active and self.outfit_ids:
                try:
                    start_time = time.time()
                    oid = self.outfit_ids[outfit_index]
                    oname = self.outfit_names[outfit_index] if outfit_index < len(self.outfit_names) else str(oid)
                    
                    details = self.outfit_cache.get(oid)
                    if not details: 
                        details = self.bot.get_outfit_details(oid)
                        if details: self.outfit_cache[oid] = details

                    if details:
                        log(f"Equipping: {oname}...", "info")
                        if "playerAvatarType" in details: self.bot.set_avatar_type(details["playerAvatarType"])
                        if "bodyColor3s" in details: self.bot.set_body_colors(details["bodyColor3s"])
                        if "assets" in details: self.bot.set_wearing_assets(details["assets"])
                    else:
                        log(f"Skipping outfit {oname} (Could not fetch details)", "warning")
                    
                    outfit_index = (outfit_index + 1) % len(self.outfit_ids)
                    
                    elapsed = time.time() - start_time
                    sleep_time = max(0, self.interval - elapsed)
                    time.sleep(sleep_time)

                except Exception as e:
                    log(f"Loop Error: {e}", "error")
                    time.sleep(self.interval)
            else:
                time.sleep(1)

    def terminate(self):
        self.running = False
        log("Program terminated by user.", "info")

# settings menu/gui
settings_window_open = False
settings_lock = threading.Lock()

def open_settings():
    if rotator.active:
        return

    try:
        subprocess.Popen([
            sys.executable,
            os.path.abspath(__file__),
            "--settings"
        ])
    except Exception as e:
        log(f"Could not open Settings: {e}", "error")

def run_settings_window():
    root = tk.Tk()
    root.title("Settings | Roblox Avatar Rotator")
    root.geometry("450x550")

    cfg = ConfigManager.load()

    # Cookie
    tk.Label(
        root,
        text="Roblox Cookie (.ROBLOSECURITY):"
    ).pack(pady=(10, 5))

    tk.Label(
        root,
        text="ⓘ This is used to send avatar change requests.\nDo not share your cookie with anyone.",
        fg="red",
        font=("Arial", 8)
    ).pack(pady=2)

    cookie_entry = tk.Entry(root, width=60, show="*")
    cookie_entry.pack(pady=5)

    if "cookie" in cfg:
        cookie_entry.insert(0, cfg["cookie"])

    # Outfits
    tk.Label(
        root,
        text="Selected Outfits:"
    ).pack(pady=(10, 2))

    listbox = Listbox(
        root,
        selectmode=MULTIPLE,
        width=50,
        height=10
    )
    listbox.pack(pady=5)

    fetched_map = {}

    # Load saved outfits
    if "outfits" in cfg and cfg["outfits"]:
        if isinstance(cfg["outfits"][0], dict):
            for i, outfit in enumerate(cfg["outfits"]):
                listbox.insert(END, outfit["name"])
                listbox.selection_set(i)
                fetched_map[outfit["name"]] = outfit["id"]

    def fetch_outfits_worker():
        cookie = cookie_entry.get().strip()

        if not cookie:
            root.after(
                0,
                lambda: messagebox.showerror(
                    "Error",
                    "Please enter a cookie first."
                )
            )
            fetch_btn.config(state="normal")
            return

        bot = RobloxAvatarManager()
        bot.update_cookie(cookie)

        user = bot.get_authenticated_user()

        if not user:
            root.after(
                0,
                lambda: messagebox.showerror(
                    "Error",
                    "Could not authenticate with that cookie."
                )
            )
            fetch_btn.config(state="normal")
            return

        outfits = bot.fetch_user_outfits()

        if not outfits:
            root.after(
                0,
                lambda: messagebox.showwarning(
                    "Warning",
                    "No outfits found or the API returned an error."
                )
            )
            fetch_btn.config(state="normal")
            return

        def update_list():
            listbox.delete(0, END)
            fetched_map.clear()

            saved_ids = []

            if cfg.get("outfits"):
                if isinstance(cfg["outfits"][0], dict):
                    saved_ids = [
                        outfit["id"]
                        for outfit in cfg["outfits"]
                    ]
                else:
                    saved_ids = cfg["outfits"]

            for i, outfit in enumerate(outfits):
                listbox.insert(END, outfit["name"])
                fetched_map[outfit["name"]] = outfit["id"]

                if outfit["id"] in saved_ids:
                    listbox.selection_set(i)

            fetch_btn.config(state="normal")

        root.after(0, update_list)

    def fetch_outfits():
        fetch_btn.config(state="disabled")

        threading.Thread(
            target=fetch_outfits_worker,
            daemon=True
        ).start()

    fetch_btn = tk.Button(
        root,
        text="Fetch My Outfits",
        command=fetch_outfits
    )
    fetch_btn.pack(pady=5)

    # Cooldown
    tk.Label(
        root,
        text="Cooldown (seconds):"
    ).pack(pady=(10, 2))

    interval_spin = tk.Spinbox(
        root,
        from_=1,
        to=300,
        width=5
    )
    interval_spin.pack()

    interval_spin.delete(0, "end")
    interval_spin.insert(
        0,
        cfg.get("interval", 5)
    )

    tk.Label(
        root,
        text="⚠ Below 3 seconds may hit API limits.",
        fg="red",
        font=("Arial", 8)
    ).pack(pady=2)

    # Windows startup — disabled on macOS
    startup_var = tk.BooleanVar(value=False)

    tk.Checkbutton(
        root,
        text="Run on Windows Startup (Windows only)",
        variable=startup_var,
        state="disabled"
    ).pack(pady=10)

    def save():
        selected_indices = listbox.curselection()

        if not selected_indices:
            messagebox.showwarning(
                "Warning",
                "No outfits selected!"
            )
            return

        selected_outfits = []

        for index in selected_indices:
            name = listbox.get(index)

            if name in fetched_map:
                selected_outfits.append({
                    "id": fetched_map[name],
                    "name": name
                })

        try:
            new_interval = int(interval_spin.get())
        except ValueError:
            new_interval = 5

        new_cfg = {
            "cookie": cookie_entry.get().strip(),
            "outfits": selected_outfits,
            "interval": new_interval
        }

        ConfigManager.save(new_cfg)

        messagebox.showinfo(
            "Saved",
            "Settings saved!"
        )

        root.destroy()

    tk.Label(
        root,
        text="Tool made by fowntain"
    ).pack(pady=(10, 5))

    tk.Button(
        root,
        text="Save & Close",
        command=save,
        height=2,
        width=20
    ).pack(pady=10)

    try:
       root.mainloop()
    finally:
        with settings_lock:
          settings_window_open = False

# sys tray stuff
# aha! youre reading the code or commit changes! gotcha.
def create_image():
    color = (0, 255, 100) if rotator.active else (255, 50, 50)
    image = Image.new('RGB', (64, 64), color=(30, 30, 30))
    dc = ImageDraw.Draw(image)
    dc.ellipse((16, 16, 48, 48), fill=color)
    return image

def update_icon(icon): icon.icon = create_image()

def on_toggle(icon, item):
    if rotator.active: rotator.stop_rotation()
    else: rotator.start_rotation()
    update_icon(icon)

def on_exit(icon, item):
    rotator.terminate()
    icon.stop()
    sys.exit()

if "--settings" in sys.argv:
    run_settings_window()
    sys.exit()

rotator = AvatarRotator()

def get_menu():
    toggle_text = "Stop" if rotator.active else "Start"
    return pystray.Menu(
        item(toggle_text, on_toggle),
        item('Settings', open_settings, enabled=lambda i: not rotator.active),
        item('View Logs', lambda: open_logs()),
        item('End Program', on_exit)
    )

icon = pystray.Icon("RobloxRotator", create_image(), menu=get_menu())

def icon_updater(icon):
    icon.visible = True
    while rotator.running:
        icon.menu = get_menu()
        update_icon(icon)
        time.sleep(1)

log("Application Started.", "info")
icon.run(setup=icon_updater)

# open_settings()
