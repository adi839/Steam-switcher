import os
import winreg
import subprocess
import time
import json
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image
import requests
from io import BytesIO
import webbrowser
import secrets
import string
import threading
import tempfile
import xml.etree.ElementTree as ET

# Important: Pentru a folosi system tray, este necesar: pip install pystray
try:
    import pystray
    from pystray import MenuItem as item
except ImportError:
    pystray = None

# --- CONFIGURARE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "steam_accounts_v3.json")
STEAM_PATH = r"C:\Program Files (x86)\Steam\steam.exe"
APP_NAME = "SteamSwitcherPro"

# Link-uri pentru Tutoriale YouTube
YT_ID_LINK = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 
YT_API_LINK = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 

# Interval de reîmprospătare (7 zile în secunde)
REFRESH_INTERVAL = 604800 

# Categorii disponibile
CATEGORIES = ["Main", "Smurf", "Storage", "Other"]

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SteamManager(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Steam Account Switcher — Pro Edition")
        self.geometry("1200x950")
        
        # Încărcare date (conturi + setări)
        self.data = self.load_data()
        self.accounts = self.data.get("accounts", [])
        self.settings = self.data.get("settings", {
            "first_run": True, 
            "run_at_startup": False,
            "collapsed_categories": []
        })
        
        self.image_refs = [] 
        
        # Variabile pentru căutare
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_list())

        # Setup Interfață
        self.setup_ui()
        
        # Gestionare închidere -> Ascundere în Tray
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        
        # Verificare prima rulare
        self.after(1000, self.check_first_run)
        
        # Curățare fișiere HTML vechi din folderul TEMP
        self.cleanup_temp_files()
        
        # Verificare actualizări săptămânale în fundal
        threading.Thread(target=self.check_auto_refresh, daemon=True).start()
        
        if pystray:
            self.setup_tray()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.setup_sidebar()

        # Container Principal
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_container.grid_rowconfigure(2, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Header
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, pady=(0, 20), sticky="ew")
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="Your Saved Accounts", font=ctk.CTkFont(size=28, weight="bold"))
        self.title_label.pack(side="left")

        self.stats_label = ctk.CTkLabel(self.header_frame, text=f"Total: {len(self.accounts)}", text_color="gray")
        self.stats_label.pack(side="right", pady=(10, 0))

        # Bara de căutare
        self.search_frame = ctk.CTkFrame(self.main_container, fg_color="#2b2b2b", corner_radius=10, height=50)
        self.search_frame.grid(row=1, column=0, pady=(0, 20), sticky="ew")
        self.search_frame.grid_propagate(False)
        
        search_icon = ctk.CTkLabel(self.search_frame, text="🔍", font=ctk.CTkFont(size=16))
        search_icon.pack(side="left", padx=15)
        
        self.search_entry = ctk.CTkEntry(self.search_frame, textvariable=self.search_var, placeholder_text="Search by name or username...", 
                                         fg_color="transparent", border_width=0, font=ctk.CTkFont(size=14))
        self.search_entry.pack(side="left", fill="both", expand=True, padx=(0, 15))

        # Zona Scrollable
        self.scroll_frame = ctk.CTkScrollableFrame(self.main_container, label_text="Account Manager", label_font=("Helvetica", 12, "bold"))
        self.scroll_frame.grid(row=2, column=0, sticky="nsew")
        
        self.refresh_list()

    def setup_sidebar(self):
        self.sb_label = ctk.CTkLabel(self.sidebar, text="ADD NEW ACCOUNT", font=ctk.CTkFont(size=16, weight="bold"))
        self.sb_label.pack(pady=(30, 15))

        self.in_display_name = ctk.CTkEntry(self.sidebar, placeholder_text="Display Name", width=260, height=35)
        self.in_display_name.pack(pady=4)

        self.in_user = ctk.CTkEntry(self.sidebar, placeholder_text="Steam Username", width=260, height=35)
        self.in_user.pack(pady=4)

        # Frame Parolă cu buton de vizualizare
        pass_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        pass_frame.pack(pady=4, fill="x", padx=30)
        self.in_pass = ctk.CTkEntry(pass_frame, placeholder_text="Steam Password", show="*", width=210, height=35)
        self.in_pass.pack(side="left")
        self.btn_show_pass = ctk.CTkButton(pass_frame, text="👁️", width=40, height=35, fg_color="#3d3d3d", hover_color="#4d4d4d", 
                                           command=self.toggle_password_visibility)
        self.btn_show_pass.pack(side="right")

        self.in_email = ctk.CTkEntry(self.sidebar, placeholder_text="Email", width=260, height=35)
        self.in_email.pack(pady=4)

        # SteamID64
        id_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        id_frame.pack(pady=4, fill="x", padx=30)
        self.in_steamid = ctk.CTkEntry(id_frame, placeholder_text="SteamID64", width=210, height=35)
        self.in_steamid.pack(side="left")
        ctk.CTkButton(id_frame, text="📺", width=40, height=35, fg_color="#cc0000", hover_color="#990000", 
                      command=lambda: webbrowser.open(YT_ID_LINK)).pack(side="right")

        # API Key
        api_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        api_frame.pack(pady=4, fill="x", padx=30)
        self.in_api = ctk.CTkEntry(api_frame, placeholder_text="Steam API Key (Opt.)", width=210, height=35)
        self.in_api.pack(side="left")
        ctk.CTkButton(api_frame, text="📺", width=40, height=35, fg_color="#cc0000", hover_color="#990000", 
                      command=lambda: webbrowser.open(YT_API_LINK)).pack(side="right")

        # Categorie
        self.category_var = ctk.StringVar(value=CATEGORIES[0])
        cat_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        cat_frame.pack(pady=4, fill="x", padx=30)
        ctk.CTkLabel(cat_frame, text="Category:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.in_category = ctk.CTkOptionMenu(cat_frame, values=CATEGORIES, variable=self.category_var, width=170, height=35)
        self.in_category.pack(side="right")

        self.in_desc = ctk.CTkEntry(self.sidebar, placeholder_text="Account Description (optional)", width=260, height=35)
        self.in_desc.pack(pady=4)

        self.guard_var = ctk.BooleanVar(value=False)
        self.guard_check = ctk.CTkSwitch(self.sidebar, text="Steam Guard Enabled", variable=self.guard_var)
        self.guard_check.pack(pady=8)

        # Label status verificare
        self.verify_label = ctk.CTkLabel(self.sidebar, text="", text_color="#aaaaaa", font=ctk.CTkFont(size=11))
        self.verify_label.pack(pady=(5, 0))

        self.btn_save = ctk.CTkButton(self.sidebar, text="SAVE ACCOUNT", command=self.add_account_flow, fg_color="#1f6aa5", height=40)
        self.btn_save.pack(pady=10, padx=30, fill="x")

        ctk.CTkLabel(self.sidebar, text="—" * 20, text_color="gray30").pack(pady=8)

        # Pornire Automată
        self.startup_var = ctk.BooleanVar(value=self.settings.get("run_at_startup", False))
        self.startup_check = ctk.CTkSwitch(self.sidebar, text="Run at System Startup", variable=self.startup_var, command=self.toggle_startup)
        self.startup_check.pack(pady=5)

        # Generator Parole
        self.btn_gen = ctk.CTkButton(self.sidebar, text="GENERATE STRONG PASS", command=self.generate_password, fg_color="transparent", border_width=1, height=30)
        self.btn_gen.pack(pady=8, padx=30, fill="x")
        self.gen_result = ctk.CTkEntry(self.sidebar, placeholder_text="Result", width=260, height=30)
        self.gen_result.pack(pady=0)

        # Link-uri Ajutor
        self.btn_api_link = ctk.CTkButton(self.sidebar, text="Get Steam API Key", command=lambda: webbrowser.open("https://steamcommunity.com/dev/apikey"), 
            fg_color="transparent", text_color="#1f6aa5", font=ctk.CTkFont(size=12, underline=True))
        self.btn_api_link.pack(pady=(15, 0))

        # Credite
        ctk.CTkLabel(self.sidebar, text="Created by: _gabyro", text_color="#555555", font=ctk.CTkFont(size=10)).pack(side="bottom", pady=10)

    def toggle_password_visibility(self):
        """Comută vizibilitatea parolei în câmpul de input."""
        if self.in_pass.cget("show") == "*":
            self.in_pass.configure(show="")
            self.btn_show_pass.configure(text="🔒")
        else:
            self.in_pass.configure(show="*")
            self.btn_show_pass.configure(text="👁️")

    def toggle_category(self, cat):
        """Închide sau deschide o categorie în listă."""
        collapsed = self.settings.get("collapsed_categories", [])
        if cat in collapsed:
            collapsed.remove(cat)
        else:
            collapsed.append(cat)
        self.settings["collapsed_categories"] = collapsed
        self.save_data()
        self.refresh_list()

    def refresh_list(self):
        """Reîmprospătează vizualizarea listei de conturi."""
        for w in self.scroll_frame.winfo_children(): w.destroy()
        self.image_refs = []
        search_term = self.search_var.get().lower()
        collapsed = self.settings.get("collapsed_categories", [])

        # Grupăm conturile pe categorii
        grouped_accounts = {cat: [] for cat in CATEGORIES}
        for acc in self.accounts:
            if search_term in acc.get('name', '').lower() or search_term in acc.get('user', '').lower():
                cat = acc.get('category', 'Other')
                if cat not in grouped_accounts: cat = 'Other'
                grouped_accounts[cat].append(acc)

        for cat, acc_list in grouped_accounts.items():
            if not acc_list: continue
            
            is_collapsed = cat in collapsed
            icon = "▶" if is_collapsed else "▼"
            
            # Antet Categorie
            cat_header = ctk.CTkFrame(self.scroll_frame, fg_color="#3d3d3d", corner_radius=5, cursor="hand2")
            cat_header.pack(fill="x", padx=10, pady=(15, 5))
            
            h_lbl = ctk.CTkLabel(cat_header, text=f"{icon} {cat.upper()}", font=ctk.CTkFont(size=12, weight="bold"))
            h_lbl.pack(pady=5, side="left", padx=10)
            
            h_lbl.bind("<Button-1>", lambda e, c=cat: self.toggle_category(c))
            cat_header.bind("<Button-1>", lambda e, c=cat: self.toggle_category(c))

            if is_collapsed: continue

            for acc in acc_list:
                card = ctk.CTkFrame(self.scroll_frame, corner_radius=12, fg_color="#2b2b2b", border_width=1, border_color="#3d3d3d")
                card.pack(fill="x", padx=15, pady=8)

                # Avatar
                img_label = ctk.CTkLabel(card, text="👤", font=ctk.CTkFont(size=30), width=80, height=80)
                if acc.get("avatar"):
                    try:
                        res = requests.get(acc["avatar"], timeout=2)
                        if res.status_code == 200:
                            img = Image.open(BytesIO(res.content))
                            photo = ctk.CTkImage(img, size=(80, 80))
                            img_label.configure(image=photo, text="")
                            self.image_refs.append(photo)
                    except: pass
                img_label.pack(side="left", padx=(15, 20), pady=15)

                # Info Section
                info = ctk.CTkFrame(card, fg_color="transparent")
                info.pack(side="left", fill="both", expand=True, pady=15)
                
                # Title & Status Bar
                title_row = ctk.CTkFrame(info, fg_color="transparent")
                title_row.pack(anchor="w")
                ctk.CTkLabel(title_row, text=acc.get("name"), font=ctk.CTkFont(size=19, weight="bold")).pack(side="left")
                
                # Render specific ban tags
                active_bans = acc.get("active_bans", [])
                if not active_bans:
                    # If no specific bans list but legacy status was "Clean"
                    if acc.get("vac_status") == "Clean":
                        ctk.CTkLabel(title_row, text="CLEAN", font=ctk.CTkFont(size=10, weight="bold"), 
                                     fg_color="#107c10", text_color="white", corner_radius=4, width=60).pack(side="left", padx=10)
                    else:
                        # For old accounts not yet refreshed with new logic
                        ctk.CTkLabel(title_row, text="CHECKING...", font=ctk.CTkFont(size=10, weight="bold"), 
                                     fg_color="gray", text_color="white", corner_radius=4, width=60).pack(side="left", padx=10)
                else:
                    for b_tag in active_bans:
                        ctk.CTkLabel(title_row, text=b_tag.upper(), font=ctk.CTkFont(size=10, weight="bold"), 
                                     fg_color="#cc0000", text_color="white", corner_radius=4, padx=5).pack(side="left", padx=5)

                # Privacy Status Badge
                p_status = acc.get("privacy_status", "Public")
                if p_status != "Public":
                    ctk.CTkLabel(title_row, text="PRIVATE", font=ctk.CTkFont(size=10, weight="bold"), 
                                           fg_color="#f39c12", text_color="black", corner_radius=4, width=60).pack(side="left", padx=5)

                if acc.get("is_limited"):
                    ctk.CTkLabel(title_row, text="LIMITED", font=ctk.CTkFont(size=10, weight="bold"), 
                                           fg_color="gray20", text_color="gray70", corner_radius=4, width=60).pack(side="left", padx=5)

                if acc.get("desc"):
                    ctk.CTkLabel(info, text=acc.get("desc"), font=ctk.CTkFont(size=12, slant="italic"), text_color="#1f6aa5").pack(anchor="w")
                
                ctk.CTkLabel(info, text=f"User: {acc.get('user')} | Email: {acc.get('email', '-')}", font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w")
                
                # Jocuri
                if acc.get("top_games"):
                    games_frame = ctk.CTkFrame(info, fg_color="transparent")
                    games_frame.pack(anchor="w", pady=(5,0))
                    ctk.CTkLabel(games_frame, text="🎮", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0,5))
                    for g_name in acc["top_games"]:
                        ctk.CTkLabel(games_frame, text=g_name, font=ctk.CTkFont(size=10), fg_color="#3d3d3d", corner_radius=4).pack(side="left", padx=2)
                    if acc.get("game_count", 0) > 3:
                        ctk.CTkButton(games_frame, text=f"+{acc['game_count']-3} more", width=40, height=20, fg_color="transparent", 
                                      text_color="#1f6aa5", hover=False, font=ctk.CTkFont(size=10, underline=True),
                                      command=lambda a=acc: self.show_full_games_list_web(a)).pack(side="left", padx=5)

                # Butoane Acțiuni
                btn_frame = ctk.CTkFrame(card, fg_color="transparent")
                btn_frame.pack(side="right", padx=20)
                ctk.CTkButton(btn_frame, text="LOGIN NOW", width=120, height=35, command=lambda a=acc: self.smart_connect(a), font=ctk.CTkFont(weight="bold")).pack(pady=5)
                sub_btn = ctk.CTkFrame(btn_frame, fg_color="transparent")
                sub_btn.pack()
                ctk.CTkButton(sub_btn, text="Copy", width=55, height=25, fg_color="#444444", command=lambda p=acc.get('pass'): self.copy_to_clip(p)).pack(side="left", padx=2)
                ctk.CTkButton(sub_btn, text="Del", width=55, height=25, fg_color="#8b0000", command=lambda u=acc['user']: self.delete_account(u)).pack(side="left", padx=2)

    def update_steam_registry(self, user):
        """Actualizează regiștrii Steam pentru a pregăti AutoLogin."""
        try:
            reg_path = r"Software\Valve\Steam"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "AutoLoginUser", 0, winreg.REG_SZ, user)
            winreg.SetValueEx(key, "RememberPassword", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Eroare Registry: {e}")
            return False

    def add_account_flow(self):
        """Procesul de adăugare a unui cont cu verificare în timp real."""
        name, user, password = self.in_display_name.get().strip(), self.in_user.get().strip(), self.in_pass.get()
        if not name or not user:
            messagebox.showerror("Error", "Name and User are required!")
            return

        self.btn_save.configure(state="disabled")
        self.verify_label.configure(text="Verification in progress...", text_color="orange")
        self.update_idletasks()

        threading.Thread(target=self.verify_and_save, args=(name, user, password), daemon=True).start()

    def verify_and_save(self, name, user, password):
        # 1. Închidere completă procese vechi
        os.system("taskkill /f /im steam.exe >nul 2>&1")
        time.sleep(2)

        if not os.path.exists(STEAM_PATH):
            self.after(0, lambda: messagebox.showerror("Error", "Steam not found!"))
            self.after(0, self.reset_save_btn)
            return

        # 2. Scrierea în regiștri înainte de pornire
        self.update_steam_registry(user)
        time.sleep(0.5)

        if self.guard_var.get():
            self.after(0, lambda: self.verify_label.configure(text="Waiting for Guard approval...", text_color="#1f6aa5"))
        
        # 3. Lansare forțată cu credențiale
        subprocess.Popen([STEAM_PATH, "-login", user, password])
        
        success = False
        start_wait = time.time()
        while time.time() - start_wait < 35:
            time.sleep(2)
            current_reg_user = self.get_steam_registry_user()
            if current_reg_user.lower() == user.lower():
                success = True
                break
            if not self.is_steam_running():
                break

        if success:
            self.after(0, lambda: self.finalize_save(name, user, password))
        else:
            self.after(0, lambda: messagebox.showwarning("Warning", "Could not verify automatically.\nPlease check if Username/Password is correct."))
            if messagebox.askyesno("Save anyway?", "Verification timed out. Save account anyway?"):
                self.after(0, lambda: self.finalize_save(name, user, password))
            else:
                self.after(0, self.reset_save_btn)

    def finalize_save(self, name, user, password):
        self.verify_label.configure(text="Fetching Steam Data...", text_color="orange")
        steam_data = self.fetch_steam_data(self.in_steamid.get().strip(), self.in_api.get().strip())
        
        self.accounts.append({
            "name": name, "user": user, "pass": password, "desc": self.in_desc.get().strip(),
            "email": self.in_email.get(), "sid": self.in_steamid.get(), "api": self.in_api.get(), 
            "category": self.category_var.get(), "guard": self.guard_var.get(), "avatar": steam_data["avatar"],
            "top_games": steam_data["games"], "all_games": steam_data.get("all_games", []),
            "game_count": steam_data.get("game_count", 0), 
            "active_bans": steam_data["active_bans"], # Store list of specific bans
            "vac_status": "Clean" if not steam_data["active_bans"] else "Banned",
            "privacy_status": steam_data.get("privacy_status", "Public"), 
            "is_limited": steam_data.get("limited", False),
            "last_update": time.time()
        })
        
        if self.save_data():
            self.refresh_list()
            for entry in [self.in_display_name, self.in_user, self.in_pass, self.in_desc, self.in_email, self.in_steamid, self.in_api]:
                entry.delete(0, tk.END)
            self.stats_label.configure(text=f"Total: {len(self.accounts)}")
            messagebox.showinfo("Success", f"Account '{name}' saved!")
        
        self.reset_save_btn()

    def reset_save_btn(self):
        self.btn_save.configure(state="normal")
        self.verify_label.configure(text="")

    def cleanup_temp_files(self):
        """Șterge fișierele HTML temporare mai vechi de 24h."""
        temp_dir = tempfile.gettempdir()
        count = 0
        current_time = time.time()
        for filename in os.listdir(temp_dir):
            if filename.startswith("steam_games_") and filename.endswith(".html"):
                file_path = os.path.join(temp_dir, filename)
                try:
                    if current_time - os.path.getmtime(file_path) > 86400:
                        os.remove(file_path)
                        count += 1
                except: pass
        if count > 0: print(f"[*] Cleaned up {count} HTML files.")

    def check_auto_refresh(self):
        """Actualizează automat datele conturilor o dată pe săptămână."""
        current_time = time.time()
        updated = False
        for acc in self.accounts:
            last_update = acc.get("last_update", 0)
            if current_time - last_update > REFRESH_INTERVAL:
                steam_data = self.fetch_steam_data(acc.get("sid"), acc.get("api"))
                acc["avatar"] = steam_data["avatar"]
                acc["top_games"] = steam_data["games"]
                acc["all_games"] = steam_data.get("all_games", [])
                acc["game_count"] = steam_data.get("game_count", 0)
                acc["active_bans"] = steam_data["active_bans"]
                acc["vac_status"] = "Clean" if not steam_data["active_bans"] else "Banned"
                acc["privacy_status"] = steam_data.get("privacy_status", "Public")
                acc["last_update"] = current_time
                updated = True
        if updated: 
            self.save_data()
            self.after(0, self.refresh_list)

    def check_first_run(self):
        if self.settings.get("first_run", True):
            if messagebox.askyesno("First Run", "Application by: _gabyro\n\nStart automatically with Windows?"):
                self.startup_var.set(True)
                self.toggle_startup()
            self.settings["first_run"] = False
            self.save_data()

    def toggle_startup(self):
        """Adaugă sau șterge aplicația din Startup prin regedit."""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if self.startup_var.get():
                script_path = os.path.abspath(__file__)
                val = f'"{script_path}"' if script_path.endswith(".exe") else f'pythonw.exe "{script_path}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, val)
                self.settings["run_at_startup"] = True
            else:
                try: winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError: pass
                self.settings["run_at_startup"] = False
            winreg.CloseKey(key)
            self.save_data()
        except Exception as e: messagebox.showerror("Error", f"Startup error: {e}")

    def setup_tray(self): pass

    def minimize_to_tray(self):
        if not pystray: 
            self.quit()
            return
        self.withdraw()
        image = Image.new('RGB', (64, 64), color=(31, 106, 165))
        menu = pystray.Menu(
            item('Show', lambda i, it: self.restore_from_tray(i)), 
            item('Exit', lambda i, it: self.exit_app(i))
        )
        self.tray_icon = pystray.Icon("SteamSwitcher", image, "Steam Account Switcher", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def restore_from_tray(self, icon):
        icon.stop()
        self.after(0, self.deiconify)

    def exit_app(self, icon):
        icon.stop()
        self.quit()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "accounts" in data: return data
                    return {"accounts": data, "settings": {"first_run": True, "run_at_startup": False, "collapsed_categories": []}}
            except: pass
        return {"accounts": [], "settings": {"first_run": True, "run_at_startup": False, "collapsed_categories": []}}

    def save_data(self):
        try:
            self.data = {"accounts": self.accounts, "settings": self.settings}
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
            with open(DATA_FILE, "w", encoding="utf-8") as f: 
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            return True
        except: return False

    def generate_password(self):
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(16))
        self.gen_result.delete(0, tk.END)
        self.gen_result.insert(0, password)
        self.clipboard_clear()
        self.clipboard_append(password)
        self.update()

    def fetch_steam_data(self, sid, api_key):
        """Strategie mixtă: API oficial sau Fallback XML."""
        result = {"avatar": None, "games": [], "active_bans": [], "privacy_status": "Public", "limited": False}
        if not sid: return result
        
        # --- FALLBACK: Date XML publice (Limitate la VAC) ---
        if not api_key:
            try:
                xml_url = f"https://steamcommunity.com/profiles/{sid}?xml=1"
                response = requests.get(xml_url, timeout=5)
                root = ET.fromstring(response.content)
                result["avatar"] = root.findtext("avatarFull")
                if root.findtext("privacyState") != "public": result["privacy_status"] = "Private Profile"
                if root.findtext("vacBanned") == "1": result["active_bans"].append("VAC BAN")
                result["limited"] = True 
                return result
            except: pass

        # --- STANDARD: API oficial Steam (DETECȚIE COMPLETĂ BANS) ---
        try:
            # 1. Avatar & Privacy
            summary_url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={api_key}&steamids={sid}"
            summary_res = requests.get(summary_url, timeout=5).json()
            players = summary_res.get('response', {}).get('players', [])
            if players:
                result["avatar"] = players[0].get('avatarfull')
                if players[0].get('communityvisibilitystate') != 3: result["privacy_status"] = "Private Profile"
            
            # 2. Jocuri
            games_url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={api_key}&steamid={sid}&include_appinfo=1&include_played_free_games=1&format=json"
            games_res = requests.get(games_url, timeout=5).json()
            if not games_res.get('response'): result["privacy_status"] = "Games Hidden"
            games = games_res.get('response', {}).get('games', [])
            if games:
                games.sort(key=lambda x: x.get('playtime_forever', 0), reverse=True)
                result["all_games"] = [{"name": g.get('name'), "playtime": g.get('playtime_forever', 0), "appid": g.get('appid'), "icon": g.get('img_icon_url')} for g in games]
                result["games"] = [g.get('name') for g in games[:3]]
                result["game_count"] = games_res.get('response', {}).get('game_count', 0)
                result["privacy_status"] = "Public"
            
            # 3. VERIFICARE DETALIATĂ BANS (Specific tags)
            ban_url = f"http://api.steampowered.com/ISteamUser/GetPlayerBans/v1/?key={api_key}&steamids={sid}"
            ban_res = requests.get(ban_url, timeout=5).json()
            ban_data = ban_res.get('players', [])
            if ban_data:
                p = ban_data[0]
                if p.get('VACBanned', False) or p.get('NumberOfVACBans', 0) > 0:
                    result["active_bans"].append("VAC BAN")
                if p.get('NumberOfGameBans', 0) > 0:
                    result["active_bans"].append("GAME BAN")
                if p.get('CommunityBanned', False):
                    result["active_bans"].append("COMMUNITY BAN")
                if p.get('EconomyBan', 'none') != 'none':
                    result["active_bans"].append("TRADE BAN")
        except: 
            pass
        return result

    def show_full_games_list_web(self, account):
        """Generează o pagină HTML profi și o deschide în browser."""
        games, name, avatar, sid = account.get('all_games', []), account.get('name', 'Steam'), account.get('avatar', ''), account.get('sid', '')
        rows_html = "".join([f'<a href="https://store.steampowered.com/app/{g["appid"]}" target="_blank" class="game-row-link"><div class="game-row"><img src="https://media.steampowered.com/steamcommunity/public/images/apps/{g["appid"]}/{g["icon"]}.jpg" class="game-icon" onerror="this.src=\'https://community.cloudflare.steamstatic.com/public/images/applications/community/default_app_icon.png\'"><div class="game-info"><div class="game-name">{g["name"]}</div><div class="game-playtime">{round(g["playtime"]/60,1)} hours</div></div><div class="view-store">View Store</div></div></a>' for g in games])
        p_link = f'<a href="https://steamcommunity.com/profiles/{sid}" target="_blank" class="steam-link-btn">Profile</a>' if sid else ""
        html_content = f"<html><head><title>{name}</title><style>body{{background:#1b2838;color:#c7d5e0;font-family:sans-serif;padding:20px}}.container{{max-width:800px;margin:auto;background:#171a21;border-radius:8px;overflow:hidden}}.header{{background:linear-gradient(to right,#2a475e,#1b2838);padding:30px;display:flex;align-items:center;justify-content:space-between}}.avatar{{width:80px;height:80px;border-radius:4px;border:2px solid #67c1f5}}.game-row{{display:flex;align-items:center;padding:12px;border-bottom:1px solid #233c51;cursor:pointer}}.game-row:hover{{background:#2a475e}}.game-icon{{width:42px;height:42px;margin-right:15px}}.game-name{{font-size:18px;color:#ebebeb}}.game-row-link{{text-decoration:none;color:inherit}}.view-store{{font-size:12px;color:#67c1f5;border:1px solid #67c1f5;padding:4px 8px;opacity:0}}.game-row:hover .view-store{{opacity:1}}</style></head><body><div class='container'><div class='header'><div style='display:flex;align-items:center'><img src='{avatar}' class='avatar'><h1 style='margin-left:20px'>{name}</h1></div>{p_link}</div><div class='game-list'>{rows_html}</div></div></body></html>"
        f_path = os.path.join(tempfile.gettempdir(), f"steam_games_{name}.html")
        with open(f_path, "w", encoding="utf-8") as f: f.write(html_content)
        webbrowser.open(f"file:///{f_path}")

    def delete_account(self, username):
        if messagebox.askyesno("Confirm", f"Delete account '{username}'?"):
            self.accounts = [a for a in self.accounts if a['user'] != username]
            self.save_data()
            self.refresh_list()

    def get_steam_registry_user(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", 0, winreg.KEY_READ)
            user, _ = winreg.QueryValueEx(key, "AutoLoginUser")
            winreg.CloseKey(key)
            return user
        except: return ""

    def is_steam_running(self):
        try:
            output = subprocess.check_output('tasklist /FI "IMAGENAME eq steam.exe"', shell=True).decode()
            return "steam.exe" in output.lower()
        except: return False

    def smart_connect(self, acc):
        """Conectare inteligentă cu scriere în regiștri și CLI login."""
        target = acc.get('user', '')
        current = self.get_steam_registry_user()
        
        if current.lower() == target.lower() and self.is_steam_running():
            if not messagebox.askyesno("Steam", f"Account '{target}' active. Force restart?"): return

        os.system("taskkill /f /im steam.exe >nul 2>&1")
        time.sleep(2)
        
        self.update_steam_registry(target)
        
        if os.path.exists(STEAM_PATH):
            subprocess.Popen([STEAM_PATH, "-login", target, acc.get('pass', '')])

if __name__ == "__main__":
    app = SteamManager()
    app.mainloop()