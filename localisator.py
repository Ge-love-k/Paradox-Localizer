import tkinter as tk
from tkinter import messagebox, filedialog
import argparse
import re
import os
import sys
from deep_translator import GoogleTranslator

class Localizer:
    def __init__(self, root, edit_path, ref_path, start_line):
        self.root = root
        self.edit_path = edit_path
        self.ref_path = ref_path
        self.lines = []
        self.ref_data = {} 
        self.current_index = start_line
        self.is_auto = False
        self.translator = GoogleTranslator(source='en', target='ru')
        
        self.line_pattern = re.compile(r'^(\s*[\w\.\-]+)(:\d*\s*)"(.*)"')
        self.var_pattern = re.compile(r'(\$[^\$]+\$|§.|\[[^\]]+\]|\\n)')

        self.load_files()
        self.setup_ui()
        self.show_current_line()

    def load_files(self):
        try:
            with open(self.edit_path, 'r', encoding='utf-8-sig') as f:
                self.lines = f.readlines()
            if self.ref_path and os.path.exists(self.ref_path):
                with open(self.ref_path, 'r', encoding='utf-8-sig') as f:
                    for line in f:
                        m = self.line_pattern.match(line)
                        if m: self.ref_data[m.group(1).strip()] = m.group(3)
        except Exception as e:
            messagebox.showerror("Error", f"Файлы не загружены: {e}")
            exit()

    def translate_safe(self, text):
        """Прячет переменные перед переводом и возвращает их после."""
        vars_found = self.var_pattern.findall(text)
        temp_text = text
        for i, v in enumerate(vars_found):
            temp_text = temp_text.replace(v, f" <{i}> ", 1)
        
        try:
            translated = self.translator.translate(temp_text)
            for i, v in enumerate(vars_found):
                translated = translated.replace(f"<{i}>", v).replace(f"< {i} >", v)
            return translated
        except:
            return text

    def setup_ui(self):
        self.root.title("Paradox Localizer 1.3")
        self.root.geometry("1000x850")
        self.root.configure(bg="#121212")

        font_main = ("Consolas", 11)
        
        self.main_frame = tk.Frame(self.root, bg="#121212", padx=20, pady=15)
        self.main_frame.pack(fill="both", expand=True)

        # Текстовые блоки
        self.create_label("REFERENCE:", "#707070")
        self.txt_ref = self.create_text_area(4, "#1a1a1a", "#81c784", font_main)
        
        self.create_label("ORIGINAL:", "#569cd6")
        self.txt_orig = self.create_text_area(4, "#1a1a1a", "#d4d4d4", font_main)

        self.create_label("TRANSLATION:", "#28a745")
        self.txt_input = self.create_text_area(7, "#252526", "#ffffff", font_main, edit=True)
        self.txt_input.focus_set()

        # инфо
        self.info_frame = tk.Frame(self.main_frame, bg="#121212")
        self.info_frame.pack(fill="x", pady=5)
        
        self.lbl_progress = tk.Label(self.info_frame, text="", fg="#888888", bg="#121212", font=("Consolas", 10))
        self.lbl_progress.pack(side="left")
        
        self.lbl_key = tk.Label(self.info_frame, text="", fg="#555555", bg="#121212", font=("Consolas", 10))
        self.lbl_key.pack(side="right")

        # кнопки
        self.btn_frame = tk.Frame(self.main_frame, bg="#121212")
        self.btn_frame.pack(fill="x", pady=10)

        self.btn_verify = tk.Button(self.btn_frame, text="AUTO-VERIFY", command=self.toggle_auto, 
                                   bg="#d32f2f", fg="white", font=("Consolas", 12, "bold"), 
                                   relief="flat", pady=15, cursor="hand2")
        self.btn_verify.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_next = tk.Button(self.btn_frame, text="SAVE & NEXT", command=self.next_line,
                                  bg="#28a745", fg="white", font=("Consolas", 12, "bold"), 
                                  relief="flat", pady=15, cursor="hand2")
        self.btn_next.pack(side="right", fill="x", expand=True, padx=(5, 0))

        self.root.bind("<Control-Return>", lambda e: self.next_line())
        self.root.bind_class("Text", "<Control-a>", lambda e: (e.widget.tag_add("sel", "1.0", "end"), "break")[1])

    def create_label(self, text, color):
        tk.Label(self.main_frame, text=text, fg=color, bg="#121212", font=("Consolas", 9, "bold")).pack(anchor="w")

    def create_text_area(self, h, bg, fg, font, edit=False):
        t = tk.Text(self.main_frame, height=h, bg=bg, fg=fg, font=font, padx=15, pady=15, relief="flat", wrap="word", insertbackground="white")
        if not edit: t.config(state="disabled")
        t.pack(fill="both", expand=True, pady=(2, 10))
        return t

    def toggle_auto(self):
        self.is_auto = not self.is_auto
        if self.is_auto:
            self.btn_verify.config(text="STOP", bg="#ff9800")
            self.run_auto()
        else:
            self.btn_verify.config(text="AUTO-VERIFY", bg="#d32f2f")

    def run_auto(self):
        if not self.is_auto: return
        eng = self.txt_orig.get("1.0", "end-1c")
        if eng.strip():
            translated = self.translate_safe(eng)
            self.txt_input.delete("1.0", tk.END)
            self.txt_input.insert("1.0", translated)
            self.root.update()
        self.next_line()
        self.root.after(100, self.run_auto)

    def show_current_line(self):
        while self.current_index < len(self.lines):
            line = self.lines[self.current_index]
            m = self.line_pattern.match(line)
            if m:
                eng = m.group(3)
                if not eng.strip():
                    self.current_index += 1
                    continue
                
                key = m.group(1).strip()
                ref = self.ref_data.get(key, "[NEW]")
                
                # обновление инфы
                total = len(self.lines)
                self.lbl_progress.config(text=f"PROGRESS: {self.current_index + 1} / {total}")
                self.lbl_key.config(text=f"KEY: {key}")
                
                self.set_text(self.txt_ref, ref)
                self.set_text(self.txt_orig, eng)
                self.txt_input.delete("1.0", tk.END)
                self.txt_input.insert("1.0", self.ref_data.get(key, eng))
                return
            self.current_index += 1
        messagebox.showinfo("Done", "Файл готов!")

    def set_text(self, w, t):
        w.config(state="normal")
        w.delete("1.0", tk.END)
        w.insert("1.0", t)
        w.config(state="disabled")

    def next_line(self):
        if self.current_index >= len(self.lines): return
        val = self.txt_input.get("1.0", "end-1c").replace('\n', ' ')
        m = self.line_pattern.match(self.lines[self.current_index])
        if m:
            ind = self.lines[self.current_index][:self.lines[self.current_index].find(m.group(1))]
            self.lines[self.current_index] = f'{ind}{m.group(1)}{m.group(2)}"{val}"\n'
            with open(self.edit_path, 'w', encoding='utf-8-sig') as f: f.writelines(self.lines)
        self.current_index += 1
        self.show_current_line()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("path", type=str, nargs='?', default=None, help="Путь к файлу локализации")
    p.add_argument("-ref", default=None)
    p.add_argument("-start", type=int, default=0)
    args = p.parse_args()
    if not args.path and len(sys.argv) > 1:
        if sys.argv[1].lower().endswith('.yml'):
            args.path = sys.argv[1]
    if not args.path:
        temp_root = tk.Tk()
        temp_root.withdraw()  # Скрываем основное окно лога
        # Поднимаем окно выбора файла на передний план
        temp_root.attributes("-topmost", True)
        
        selected_path = filedialog.askopenfilename(
            title="Выберите файл .yml для перевода",
            filetypes=[("Paradox Localization", "*.yml")]
        )
        
        if selected_path:
            args.path = selected_path
        else:
            print("Файл не выбран. Завершение работы.")
            sys.exit()
            
        temp_root.destroy()
    root = tk.Tk()
    app = Localizer(root, args.path, args.ref, args.start)
    root.mainloop()