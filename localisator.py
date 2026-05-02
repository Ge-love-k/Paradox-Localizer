import json
import math
from PIL import Image, ImageDraw
import customtkinter as ctk
from tkinter import messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import re
import os
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path
from googletrans import Translator
from ctypes import windll

# Константы для фикса таскбара (WinAPI)
GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
LANGUAGES = ["RU", "EN", "DE", "FR", "ES", "BR", "JA", "KO", "PO", "ZH-CN", "auto"]
LANGUAGES_ADJ = {
    "RU": "l_russian",
    "EN": "l_english",
    "DE": "l_german",
    "FR": "l_french",
    "ES": "l_spanish",
    "BR": "l_braz_por",
    "JA": "l_japanese",
    "KO": "l_korean",
    "ZH-CN": "l_simp_chinese",
    "PO": "l_polish"
}

SOCIAL_CONFIG_FILE = "social_links.json"
SOCIAL_CONFIG_URL = "https://gist.githubusercontent.com/Ge-love-k/52e99ea1315ff855ea6273029cdc19a3/raw/f8ec5d93b9c235ea48dfe3d1b13bf6aa6896d3f9/links.json"
DEFAULT_SOCIAL_URLS = {
    "Telegram": "https://t.me/your_username",
    "Discord": "https://discord.gg/your_invite",
    "Steam": "https://store.steampowered.com/"
}

ctk.set_appearance_mode("dark")

class Localizer(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, edit_path=None):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)
        
        self.title("SFN-LOCALIZER v1.4")
        self.geometry("1200x850")
        self.configure(fg_color="#000000")
        
        self.overrideredirect(True)
        self.after(100, self.set_appwindow)
        
        self.edit_path = edit_path
        self.current_index = 0
        self.bg_step = 0
        self.accent = "#00B4FF"
        self.lines = []
        self.is_auto = False
        
        self.skip_translated = ctk.BooleanVar(value=False)
        self.start_line_index = ctk.StringVar(value="0")
        
        self.line_pattern = re.compile(r'^(\s*[\w\.\-]+)(:\d*\s*)"(.*)"')
        self.var_pattern = re.compile(r'(\$[^\$]+\$|§.|\[[^\]]+\]|\\n)')
        self.cyrillic_pattern = re.compile(r'[а-яА-ЯёЁ]')
        self.shutdown_after = ctk.BooleanVar(value=False)
        self.side_panel_visible = True

        self.setup_ui()
        self.setup_drag()
        self.animate_interface()
        
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_drop)
        self.translator = Translator()
        self.social_urls = self.load_social_urls()

    def set_appwindow(self):
        """Фикс отображения в таскбаре для overrideredirect окон"""
        try:
            hwnd = windll.user32.GetParent(self.winfo_id())
            style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style & ~WS_EX_TOOLWINDOW
            style = style | WS_EX_APPWINDOW
            windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            self.withdraw()
            self.after(10, self.deiconify)
        except: pass

    def setup_ui(self):
        self.title_bar = ctk.CTkFrame(self, fg_color="#000000", height=60, corner_radius=0)
        self.title_bar.pack(fill="x", side="top")
        
        ctk.CTkLabel(self.title_bar, text="SFN-LOCALIZER v1.4", 
                     text_color="#555555", font=("Segoe UI", 10, "bold")).pack(side="left", padx=40)

        settings_icon_path = Path(__file__).resolve().parent / "icons" / "settings.png"
        if settings_icon_path.exists():
            self.icon_settings = ctk.CTkImage(light_image=Image.open(settings_icon_path), size=(16, 16))
        else:
            self.icon_settings = ctk.CTkImage(light_image=self._build_icon("#888888", "S"), size=(16, 16))

        ctk.CTkButton(self.title_bar, text="✕", fg_color="transparent", hover_color="#E81123",
                      text_color="#555555", width=60, height=60, corner_radius=0,
                      font=("Segoe UI", 12), command=self.destroy).pack(side="right")

        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.pack(fill="both", expand=True)

        self.social_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.social_bar.place(relx=0.99, rely=0.99, anchor="se")
        self.social_bar.lift()

        self.settings_button = ctk.CTkButton(self, text="", image=self.icon_settings, width=40, height=40,
                                              fg_color="#222222", hover_color="#444444", corner_radius=12,
                                              border_width=1, border_color="#555555",
                                              command=self.toggle_side_panel)
        self.settings_button.place(relx=0.01, rely=0.99, anchor="sw")
        self.settings_button.lift()

        self.side_panel = ctk.CTkFrame(self.main_area, fg_color="#080808", width=250, corner_radius=0)
        self.side_panel.pack(side="left", fill="y", padx=(20, 0), pady=20)
        self.side_panel.pack_propagate(False)


        ctk.CTkLabel(self.side_panel, text="ENGINE SETTINGS", text_color=self.accent, 
                     font=("Segoe UI", 9, "bold")).pack(pady=(30, 20))

        ctk.CTkSwitch(self.side_panel, text="SKIP TRANSLATED", variable=self.skip_translated, 
                      progress_color=self.accent).pack(pady=10, padx=30, anchor="w")
        
        ctk.CTkLabel(self.side_panel, text="START FROM LINE:", text_color="#555555", 
                     font=("Segoe UI", 8, "bold")).pack(pady=(20, 5), anchor="w", padx=30)
        
        self.start_entry = ctk.CTkEntry(self.side_panel, textvariable=self.start_line_index, 
                                        fg_color="#151515", border_color="#333333", justify="center")
        self.start_entry.pack(fill="x", padx=30)
        
        ctk.CTkButton(self.side_panel, text="APPLY START", fg_color="#222222", hover_color="#333333",
                      command=self.apply_start_index).pack(pady=15, padx=30, fill="x")

        self.card = ctk.CTkFrame(self.main_area, width=700, height=580, fg_color="#111111", corner_radius=15)
        self.card.place(relx=0.57, rely=0.5, anchor="center")
        self.card.pack_propagate(False)
        
        self.create_field("ORIGINAL", "txt_orig", 110)
        self.create_field("TRANSLATION", "txt_input", 160, active=True)
        self.filename = ctk.CTkLabel(self.card, text="", text_color="#333333", font=("Consolas", 15))
        self.filename.pack(side="bottom", pady=10)

        self.filename.configure(text=os.path.basename(self.edit_path) if self.edit_path else "")

        self.footer = ctk.CTkFrame(self.card, fg_color="transparent")
        self.footer.pack(fill="x", side="bottom", padx=40, pady=35)

        self.lbl_stats = ctk.CTkLabel(self.footer, text="0 / 0 (0%)", text_color="#666666", font=("Consolas", 12))
        self.lbl_stats.pack(side="left")

        self.btn_next = ctk.CTkButton(self.footer, text="PROCEED  ➔", fg_color=self.accent, 
                                      hover_color="#0081B3", font=("Segoe UI", 12, "bold"),
                                      width=160, height=45, command=self.next_line)
        self.btn_next.pack(side="right")

        self.btn_auto = ctk.CTkButton(self.footer, text="TURBO", fg_color="#222222", 
                                      text_color=self.accent, font=("Segoe UI", 12, "bold"),
                                      width=120, height=45, command=self.toggle_auto)
        self.btn_auto.pack(side="right", padx=15)
        self.backBtn = ctk.CTkButton(self.footer, text="← BACK", fg_color="#222222", command=self.go_back, hover_color="#333333",
                                      font=("Segoe UI", 12, "bold"), width=120, height=45, text_color=self.accent)
        self.backBtn.pack(side="right")
        self.shutdown_sw = ctk.CTkSwitch(self.side_panel, text="SHUTDOWN ON END", 
                                 variable=self.shutdown_after, progress_color="#FF3B30")
        self.shutdown_sw.pack(pady=10, padx=30, anchor="w")
        self.firstLangLabel = ctk.CTkLabel(self.side_panel, text="SOURCE LANGUAGE:", text_color="#555555", font=("Segoe UI", 15, "bold"))
        self.firstLangLabel.pack(pady=(20, 5), padx=30, anchor="w")
        self.firstLang = ctk.CTkComboBox(self.side_panel, values=LANGUAGES, state="readonly", fg_color="#151515", border_color="#333333")
        self.firstLang.pack(pady=10, padx=30, anchor="w")
        self.firstLang.set('EN')
        self.secondLangLabel = ctk.CTkLabel(self.side_panel, text="TARGET LANGUAGE:", text_color="#555555", font=("Segoe UI", 15, "bold"))
        self.secondLangLabel.pack(pady=(20, 5), padx=30, anchor="w")
        self.secondLang = ctk.CTkComboBox(self.side_panel, values=LANGUAGES[:-1], state="readonly", fg_color="#151515", border_color="#333333")
        self.secondLang.pack(pady=10, padx=30, anchor="w")
        self.secondLang.set('RU')
        self.tweak_name_and_l = ctk.CTkButton(self.side_panel, text="Change file name and l_[lang]", fg_color="#222222", command=self.tweak_name_and_l_lang, hover_color="#333333")
        self.tweak_name_and_l.pack(pady=5, padx=30, fill="x")
        self.openFileBtn = ctk.CTkButton(self.side_panel, text="Open current file", fg_color="#222222", command=self.open_current_file, hover_color="#333333")
        self.openFileBtn.pack(pady=5, padx=30, fill="x")

        telegram_icon_path = Path(__file__).resolve().parent / "icons" / "telegram.png"
        discord_icon_path = Path(__file__).resolve().parent / "icons" / "discord.png"
        steam_icon_path = Path(__file__).resolve().parent / "icons" / "_steam.png"

        if telegram_icon_path.exists():
            self.icon_telegram = ctk.CTkImage(light_image=Image.open(telegram_icon_path), size=(16, 16))
        else:
            self.icon_telegram = ctk.CTkImage(light_image=self._build_icon("#2AABEE", "T"), size=(16, 16))

        if discord_icon_path.exists():
            self.icon_discord = ctk.CTkImage(light_image=Image.open(discord_icon_path), size=(16, 16))
        else:
            self.icon_discord = ctk.CTkImage(light_image=self._build_icon("#7289DA", "D"), size=(16, 16))

        if steam_icon_path.exists():
            self.icon_steam = ctk.CTkImage(light_image=Image.open(steam_icon_path), size=(16, 16))
        else:
            self.icon_steam = ctk.CTkImage(light_image=self._build_icon("#171A21", "S"), size=(16, 16))

        ctk.CTkButton(self.social_bar, text="", image=self.icon_telegram, width=34, height=34, fg_color="#111111",
                      hover_color="#1C7ED6", command=lambda: self.open_social("Telegram")).pack(side="left", padx=(0, 8), pady=4)
        ctk.CTkButton(self.social_bar, text="", image=self.icon_discord, width=34, height=34, fg_color="#111111",
                      hover_color="#3A3C41", command=lambda: self.open_social("Discord")).pack(side="left", padx=(0, 8), pady=4)
        ctk.CTkButton(self.social_bar, text="", image=self.icon_steam, width=34, height=34, fg_color="#111111",
                      hover_color="#444444", command=lambda: self.open_social("Steam")).pack(side="left", pady=4)


    def create_field(self, title, name, h, active=False):
        ctk.CTkLabel(self.card, text=title, text_color=self.accent if active else "#444444", 
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=45, pady=(20, 5))
        t = ctk.CTkTextbox(self.card, height=h, fg_color="#050505", 
                           border_color=self.accent if active else "#222222", border_width=1)
        t.pack(fill="x", padx=40)
        if not active: t.configure(state="disabled")
        setattr(self, name, t)

    def setup_drag(self):
        def start_move(event):
            self._drag_data_x = event.x
            self._drag_data_y = event.y
        def do_move(event):
            x = self.winfo_x() + (event.x - self._drag_data_x)
            y = self.winfo_y() + (event.y - self._drag_data_y)
            self.geometry(f"+{x}+{y}")
        self.title_bar.bind("<Button-1>", start_move)
        self.title_bar.bind("<B1-Motion>", do_move)

    def toggle_side_panel(self):
        if self.side_panel_visible:
            self.side_panel.pack_forget()
            self.side_panel_visible = False
        else:
            self.side_panel.pack(side="left", fill="y", padx=(20, 0), pady=20)
            self.side_panel_visible = True

    def toggle_side_panel(self):
        if self.side_panel_visible:
            self.side_panel.pack_forget()
            self.side_panel_visible = False
        else:
            self.side_panel.pack(side="left", fill="y", padx=(20, 0), pady=20)
            self.side_panel_visible = True

    def _build_icon(self, bg_color, letter):
        img = Image.new("RGBA", (16, 16), bg_color)
        draw = ImageDraw.Draw(img)
        if letter == "T":
            draw.rectangle((4, 3, 11, 5), fill="white")
            draw.rectangle((7, 3, 9, 14), fill="white")
        elif letter == "D":
            draw.rectangle((4, 4, 11, 11), fill="white")
            draw.rectangle((4, 5, 6, 10), fill=bg_color)
            draw.rectangle((8, 5, 10, 10), fill=bg_color)
        elif letter == "S":
            draw.rectangle((4, 4, 11, 6), fill="white")
            draw.rectangle((4, 8, 11, 10), fill="white")
            draw.rectangle((4, 11, 11, 13), fill="white")
        return img

    def toggle_auto(self):
        self.is_auto = not self.is_auto
        self.btn_auto.configure(fg_color="#FF9800" if self.is_auto else "#222222", 
                                text_color="white" if self.is_auto else self.accent)
        if self.is_auto: self.run_auto()

    def run_auto(self):
        if not self.is_auto: return
        eng = self.txt_orig.get("1.0", "end-1c")
        if eng.strip():
            res = self.translate_turbo(eng)
            self.txt_input.delete("1.0", "end")
            self.txt_input.insert("1.0", res)
            self.update()
        self.next_line()
        self.after(10, self.run_auto)

    def translate_turbo(self, text):
        """Перевод через googletrans с защитой от поломки переменных"""
        if not text: return ""
        
        vars_found = self.var_pattern.findall(text)
        temp_text = text
        for i, v in enumerate(vars_found):
            temp_text = temp_text.replace(v, f" __{i}__ ", 1)
            
        try:
            res_obj = self.translator.translate(temp_text, src=self.firstLang.get(), dest=self.secondLang.get())
            res = res_obj.text
            
            for i, v in enumerate(vars_found):
                res = res.replace(f"__{i}__", v).replace(f"__ {i} __", v)
            return res
        except Exception as e:
            print(f"Ошибка перевода: {e}")
            return text 

    def next_line(self):
        if not self.lines or self.current_index >= len(self.lines): return
        val = self.txt_input.get("1.0", "end-1c").replace('\n', ' ')
        m = self.line_pattern.match(self.lines[self.current_index])
        if m:
            p = self.lines[self.current_index][:self.lines[self.current_index].find(m.group(1))]
            self.lines[self.current_index] = f'{p}{m.group(1)}{m.group(2)}"{val}"\n'
            if self.current_index % 10 == 0:
                with open(self.edit_path, 'w', encoding='utf-8-sig') as f: f.writelines(self.lines)
        self.current_index += 1
        self.show_current_line()

    def show_current_line(self):
        while self.current_index < len(self.lines):
            line = self.lines[self.current_index]
            m = self.line_pattern.match(line)
            if m:
                eng = m.group(3)
                if self.skip_translated.get() and self.cyrillic_pattern.search(eng):
                    self.current_index += 1
                    continue
                if not eng.strip():
                    self.current_index += 1
                    continue
                
                self.lbl_stats.configure(text=f"{self.current_index+1} / {len(self.lines)} ({(self.current_index+1)*100//len(self.lines)}%)")
                self.start_line_index.set(str(self.current_index))
                
                self.txt_orig.configure(state="normal")
                self.txt_orig.delete("1.0", "end")
                self.txt_orig.insert("1.0", eng)
                self.txt_orig.configure(state="disabled")
                
                self.txt_input.delete("1.0", "end")
                self.txt_input.insert("1.0", eng)
                return
            self.current_index += 1
        self.finish_work()
        messagebox.showinfo("SFN-Translator", "WORK COMPLETE")

    def load_social_urls(self):
        config_path = Path(__file__).resolve().parent / SOCIAL_CONFIG_FILE
        urls = DEFAULT_SOCIAL_URLS.copy()
        key_map = {
            'telegram': 'Telegram',
            'discord': 'Discord',
            'steam': 'Steam'
        }

        def normalize_data(data):
            if not isinstance(data, dict):
                return {}
            if 'links' in data and isinstance(data['links'], dict):
                data = data['links']
            normalized = {}
            for key, value in data.items():
                if not isinstance(value, str):
                    continue
                normalized[key_map.get(key.lower(), key)] = value
            return normalized

        remote_loaded = False
        try:
            with urllib.request.urlopen(SOCIAL_CONFIG_URL, timeout=5) as resp:
                remote_data = json.loads(resp.read().decode('utf-8'))
                remote_urls = normalize_data(remote_data)
                if remote_urls:
                    urls.update(remote_urls)
                    remote_loaded = True
        except (urllib.error.URLError, ValueError, Exception):
            pass

        if not remote_loaded and config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    local_data = json.load(f)
                urls.update(normalize_data(local_data))
            except Exception:
                pass
        elif not config_path.exists():
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(DEFAULT_SOCIAL_URLS, f, ensure_ascii=False, indent=4)
            except Exception:
                pass

        return urls

    def open_social(self, site_name):
        """Открывает ссылку на соцсеть из загруженного JSON-конфига."""
        url = self.social_urls.get(site_name)
        if url:
            webbrowser.open(url)
        else:
            messagebox.showwarning("Соцсеть не настроена", f"URL для {site_name} не задан в {SOCIAL_CONFIG_FILE}.")

    def finish_work(self):
        """Логика завершения работы"""
        
        if self.shutdown_after.get():
            # Запускаем выключение через 60 секунд
            # /s - завершение работы, /t 60 - таймер
            os.system("shutdown /s /t 60")
            messagebox.showwarning("SYSTEM", "PC will shutdown in 60s! Use 'shutdown -a' in CMD to cancel.")

    def apply_start_index(self):
        try:
            self.current_index = int(self.start_line_index.get())
            self.show_current_line()
        except: pass

    def animate_interface(self):
        ratio = (math.sin(self.bg_step) + 1) / 2
        g = int(100 + (220 - 100) * ratio)
        self.txt_input.configure(border_color=f'#00{g:02x}ff') 
        self.bg_step += 0.08
        self.after(50, self.animate_interface)

    def handle_drop(self, event):
        path = event.data.strip('{ }')
        if path.lower().endswith('.yml'):
            self.edit_path = path
            self.current_index = 0
            with open(self.edit_path, 'r', encoding='utf-8-sig') as f: 
                self.lines = f.readlines()
            self.filename.configure(text=os.path.basename(self.edit_path))
            self.show_current_line()
    def tweak_name_and_l_lang(self):
        """Изменяет название файла на l_[targetlang].yml и меняет l_[sourcelang] на l_[targetlang] в файле"""
        if not self.edit_path: return
        target_lang = self.secondLang.get()
        if target_lang == "auto":
            messagebox.showerror("Error", "Please select a target language other than 'auto'.")
            return
        
        new_path = re.sub(r'l_[\w-]+\.yml$', f'{LANGUAGES_ADJ[target_lang]}.yml', self.edit_path)
        try:
            os.rename(self.edit_path, new_path)
            self.edit_path = new_path
            self.filename.configure(text=os.path.basename(self.edit_path))
            
            self.lines[0] = f'{LANGUAGES_ADJ[target_lang]}:\n'
            
            with open(self.edit_path, 'w', encoding='utf-8-sig') as f:
                f.writelines(self.lines)
            
            messagebox.showinfo("Success", f"File renamed to {os.path.basename(new_path)} and l_[sourcelang] replaced.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
    def open_current_file(self):
        """Открывает текущий файл"""
        if not self.edit_path: return
        os.startfile(self.edit_path)
    def go_back(self):
        """Открывает предыдущую строку для редактирования"""
        if self.current_index > 1:
            self.current_index -= 2
            self.show_current_line()

if __name__ == "__main__":
    app = Localizer()
    app.mainloop()