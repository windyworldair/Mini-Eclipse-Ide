import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, Menu, messagebox
import subprocess
import os
import time
import threading
import queue

# ============================================
# 1. EDITOR TAB CLASS
# ============================================
class EditorTab:
    def __init__(self, master, file_path=None):
        self.frame = ctk.CTkFrame(master, fg_color="transparent")
        self.filepath = file_path
        self.unsaved = False

        # Editor components
        self.line_numbers = tk.Text(self.frame, width=4, padx=5, pady=5,
                                    bg="#252526", fg="#858585", state='disabled',
                                    bd=0, font=("Consolas", 13))
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        self.text_editor = tk.Text(
            self.frame, bg="#1e1e1e", fg="#d4d4d4", bd=0,
            insertbackground="white", font=("Consolas", 13),
            wrap=tk.NONE, undo=True, padx=10, pady=5
        )
        self.text_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_editor.config(tabs=4)

        # Scrollbar
        scrollbar = tk.Scrollbar(self.frame, command=self.sync_scroll)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_editor.config(yscrollcommand=scrollbar.set)
        self.line_numbers.config(yscrollcommand=scrollbar.set)

    def sync_scroll(self, *args):
        self.line_numbers.yview_moveto(args[0])
        self.text_editor.yview_moveto(args[0])

    def get_content(self):
        return self.text_editor.get("1.0", "end-1c")

    def set_content(self, content):
        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert("1.0", content)


# ============================================
# 2. SPLASH SCREEN (FIXED – single root)
# ============================================
class SplashScreen:
    def __init__(self, root, on_complete):
        self.root = root
        self.on_complete = on_complete

        self.splash = ctk.CTkToplevel(root)
        self.splash.title("")
        self.splash.geometry("400x250")
        self.splash.overrideredirect(True)
        self.splash.attributes("-topmost", True)

        # Center splash
        self.splash.update_idletasks()
        x = (root.winfo_screenwidth() - 400) // 2
        y = (root.winfo_screenheight() - 250) // 2
        self.splash.geometry(f"400x250+{x}+{y}")

        # Hide main window while loading
        root.withdraw()

        # UI
        ctk.CTkLabel(self.splash, text="🚀", font=("Segoe UI", 48)).pack(pady=(30, 5))
        ctk.CTkLabel(self.splash, text="Mini Eclipse",
                     font=("Segoe UI", 24, "bold")).pack()
        ctk.CTkLabel(self.splash, text="Python IDE",
                     font=("Segoe UI", 12)).pack(pady=(0, 20))

        self.progress = ctk.CTkProgressBar(self.splash, width=300, height=16)
        self.progress.pack()
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(self.splash, text="Initializing...")
        self.status_label.pack(pady=15)

        self.load_step = 0
        self.start_loading()

    def start_loading(self):
        self.load_step += 1
        self.progress.set(self.load_step / 100)
        self.status_label.configure(text=f"Loading... {self.load_step}%")

        if self.load_step < 100:
            self.splash.after(20, self.start_loading)
        else:
            self.splash.after(300, self.finish_loading)

    def finish_loading(self):
        self.splash.destroy()
        self.root.deiconify()   # show main window
        self.on_complete()

# ============================================
# 3. ICON MANAGER
# ============================================
class IconManager:
    def __init__(self):
        self.icons = {
            "py": "🐍",
            "folder": "📁",
            "file": "📄",
            "run": "▶",
            "debug": "🐞",
            "explorer": "📁",
            "theme_dark": "🌙",
            "theme_light": "☀️",
            "terminal": "📟",
            "close": "❌"
        }

    def get(self, key):
        return self.icons.get(key, "📄")

# ============================================
# 4. MAIN IDE
# ============================================
class MiniEclipseIDE:
    def __init__(self, root):
        self.root = root
        self.root.title("Mini Eclipse - Python IDE")
        self.root.geometry("1300x900")

        # Center main window
        self.center_window()

        # Icon manager
        self.icons = IconManager()
        self.explorer_items = {}
        # Theme
        self.is_dark = True
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # State
        self.tabs = {}
        self.tab_count = 0
        self.folder_path = None
        self.debugger_process = None
        self.debugger_input_queue = queue.Queue()

        self.setup_ui()

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_ui(self):
        # ========== MENU BAR ==========
        menubar = Menu(self.root, font=("Segoe UI", 10))
        self.root.config(menu=menubar)

        # File menu
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As...", accelerator="Ctrl+Shift+S", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Close Tab", accelerator="Ctrl+W", command=self.close_current_tab)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Edit menu
        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=lambda: self.get_active_tab().text_editor.event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=lambda: self.get_active_tab().text_editor.event_generate("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X", command=lambda: self.get_active_tab().text_editor.event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=lambda: self.get_active_tab().text_editor.event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=lambda: self.get_active_tab().text_editor.event_generate("<<Paste>>"))

        # View menu
        view_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Explorer", command=self.toggle_explorer)
        view_menu.add_command(label="Toggle Terminal", command=self.toggle_terminal)
        view_menu.add_separator()
        view_menu.add_command(label="Dark Theme", command=lambda: self.set_theme("dark"))
        view_menu.add_command(label="Light Theme", command=lambda: self.set_theme("light"))

        # Run menu
        run_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(label="Run Python File", command=self.run_python, accelerator="F5")
        run_menu.add_command(label="Debug", command=self.debug_python, accelerator="F6")
        run_menu.add_command(label="Run Selection", command=self.run_selection, accelerator="F9")

        # Help menu
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        # ========== TOOLBAR ==========
        toolbar_frame = ctk.CTkFrame(self.root, height=42, fg_color="transparent")
        toolbar_frame.pack(side=tk.TOP, fill=tk.X, padx=8, pady=3)

        # Emoji buttons
        btn_style = {
            "width": 38, "height": 34, "corner_radius": 6,
            "fg_color": "transparent", "hover_color": ("#e0e0e0", "#3a3a3a"),
            "text_color": ("black", "white"), "font": ("Segoe UI Emoji", 18)
        }

        self.run_btn = ctk.CTkButton(toolbar_frame, text=self.icons.get("run"),
                                     command=self.run_python, **btn_style)
        self.run_btn.pack(side=tk.LEFT, padx=3)

        self.debug_btn = ctk.CTkButton(toolbar_frame, text=self.icons.get("debug"),
                                       command=self.debug_python, **btn_style)
        self.debug_btn.pack(side=tk.LEFT, padx=3)

        self.explorer_btn = ctk.CTkButton(toolbar_frame, text=self.icons.get("explorer"),
                                          command=self.toggle_explorer, **btn_style)
        self.explorer_btn.pack(side=tk.LEFT, padx=3)

        self.theme_btn = ctk.CTkButton(toolbar_frame, text=self.icons.get("theme_dark"),
                                       command=self.toggle_theme, **btn_style)
        self.theme_btn.pack(side=tk.LEFT, padx=3)

        # Separator
        sep = ctk.CTkFrame(toolbar_frame, width=1, height=26, fg_color=("#ccc", "#555"))
        sep.pack(side=tk.LEFT, padx=12)

        # File label
        self.file_label = ctk.CTkLabel(toolbar_frame, text="No file open",
                                       font=("Segoe UI", 10), anchor="w")
        self.file_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        # ========== MAIN PANEL ==========
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Left: Explorer
        self.setup_explorer(main_container)

        # Center: Editor
        self.setup_editor(main_container)

        # Bottom: Terminal
        self.setup_terminal()

        # Initial tab
        self.new_file()

    def setup_explorer(self, parent):
        self.explorer_frame = ctk.CTkFrame(parent, width=230, corner_radius=8)
        self.explorer_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        self.explorer_frame.pack_propagate(False)

        ctk.CTkLabel(self.explorer_frame, text="EXPLORER",
                     font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(12, 5))

        # Buttons
        btn_frame = ctk.CTkFrame(self.explorer_frame, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ctk.CTkButton(btn_frame, text="Open File", width=100, height=28,
                      command=self.open_file).pack(side=tk.LEFT, padx=2)
        ctk.CTkButton(btn_frame, text="Open Folder", width=100, height=28,
                      command=self.open_folder).pack(side=tk.LEFT, padx=2)

        # File list with icons
        list_frame = ctk.CTkFrame(self.explorer_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        self.explorer_text = tk.Text(list_frame, bg="#2b2b2b", fg="white", bd=0,
                                     font=("Segoe UI", 11), height=15)
        self.explorer_text.pack(fill=tk.BOTH, expand=True)
        self.explorer_text.bind("<Double-Button-1>", self.on_explorer_double_click)
        self.explorer_text.config(state='disabled')

    def refresh_explorer(self):
        self.explorer_text.config(state='normal')
        self.explorer_text.delete('1.0', 'end')
        self.explorer_items.clear()

        if self.folder_path:
            self.explorer_text.insert('end',
                                      f"{self.icons.get('folder')} {os.path.basename(self.folder_path)}\n")

            line = 2
            for f in sorted(os.listdir(self.folder_path)):
                full = os.path.join(self.folder_path, f)

                if os.path.isdir(full):
                    self.explorer_text.insert('end',
                                              f"  {self.icons.get('folder')} {f}/\n")
                else:
                    icon = self.icons.get("py") if f.endswith(".py") else self.icons.get("file")
                    self.explorer_text.insert('end',
                                              f"  {icon} {f}\n")
                    self.explorer_items[line] = full

                line += 1

        self.explorer_text.config(state='disabled')

    def on_explorer_double_click(self, event):
        index = self.explorer_text.index(f"@{event.x},{event.y}")
        line = int(index.split('.')[0])

        path = self.explorer_items.get(line)
        if path and os.path.isfile(path):
            self.load_file(path)

    def setup_editor(self, parent):
        self.tab_view = ctk.CTkTabview(parent)
        self.tab_view.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

    def on_text_change(self, event=None):
        active_tab = self.get_active_tab()
        if active_tab and not active_tab.unsaved:
            active_tab.unsaved = True
            tab_name = self.tab_view.get()
            base_name = os.path.basename(active_tab.filepath) if active_tab.filepath else "Untitled"
            self.tab_view.tab(tab_name, text=f"{base_name}*")

        self.update_line_numbers()

    def update_line_numbers(self, event=None):
        active_tab = self.get_active_tab()
        if not active_tab:
            return

        lines = active_tab.text_editor.get('1.0', 'end').count('\n')
        active_tab.line_numbers.config(state='normal')
        active_tab.line_numbers.delete('1.0', 'end')
        active_tab.line_numbers.insert('1.0', '\n'.join(str(i) for i in range(1, lines + 1)))
        active_tab.line_numbers.config(state='disabled')
        self.apply_syntax_highlighting()

    def setup_terminal(self):
        self.output_frame = ctk.CTkFrame(self.root, corner_radius=8)
        self.output_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False, padx=8, pady=(0, 8))
        self.output_frame.configure(height=250)

        output_header = ctk.CTkFrame(self.output_frame, height=30, fg_color="transparent")
        output_header.pack(fill=tk.X, padx=10, pady=(8, 0))
        ctk.CTkLabel(output_header, text="OUTPUT",
                     font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)

        ctk.CTkButton(output_header, text="Clear", width=60, height=24,
                      command=self.clear_output).pack(side=tk.RIGHT, padx=5)

        self.terminal_output = tk.Text(
            self.output_frame, bg="#0c0c0c", fg="#cccccc", bd=0,
            height=15, font=("Consolas", 11), padx=10, pady=5
        )
        self.terminal_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.terminal_output.insert('1.0', ">>> Mini Eclipse Terminal - Ready\n")
        self.terminal_output.bind("<Return>", self.on_terminal_enter)

        t_scroll = tk.Scrollbar(self.output_frame, command=self.terminal_output.yview)
        t_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.terminal_output.config(yscrollcommand=t_scroll.set)

    def on_terminal_enter(self, event):
        if self.debugger_process:
            command = self.terminal_output.get("end-2l linestart", "end-1c")
            self.debugger_input_queue.put(command + '\n')
            return "break"

    def get_active_tab(self):
        tab_name = self.tab_view.get()
        return self.tabs.get(tab_name)

    # ========== FILE OPERATIONS ==========
    def new_file(self):
        self.tab_count += 1
        tab_name = f"Untitled-{self.tab_count}"

        tab_widget = self.tab_view.add(tab_name)
        editor = EditorTab(tab_widget)
        editor.frame.pack(fill=tk.BOTH, expand=True)
        self.tabs[tab_name] = editor

        editor.text_editor.bind('<KeyRelease>', self.on_text_change)

        sample = '''# Welcome to Mini Eclipse
print("Hello, World!")'''
        editor.set_content(sample)
        self.tab_view.set(tab_name)
        self.update_line_numbers()

    def open_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Python files", "*.py"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            self.load_file(filepath)

    def open_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path = folder
            self.refresh_explorer()

    def load_file(self, filepath):
        for tab_name, tab in self.tabs.items():
            if tab.filepath == filepath:
                self.tab_view.set(tab_name)
                return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            tab_name = os.path.basename(filepath)
            tab_widget = self.tab_view.add(tab_name)

            editor = EditorTab(tab_widget, file_path=filepath)
            editor.frame.pack(fill=tk.BOTH, expand=True)
            editor.set_content(content)

            self.tabs[tab_name] = editor
            editor.text_editor.bind('<KeyRelease>', self.on_text_change)

            self.tab_view.set(tab_name)
            self.file_label.configure(text=f"File: {filepath}")
            self.update_line_numbers()
            self.log_output(f"[INFO] Loaded: {filepath}")
        except Exception as e:
            self.log_output(f"[ERROR] {e}")

    def save_file(self):
        active_tab = self.get_active_tab()
        if not active_tab:
            return

        if active_tab.filepath:
            try:
                with open(active_tab.filepath, 'w', encoding='utf-8') as f:
                    f.write(active_tab.get_content())

                active_tab.unsaved = False
                tab_name = self.tab_view.get()
                self.tab_view.tab(tab_name, text=os.path.basename(active_tab.filepath))
                self.log_output(f"[INFO] Saved: {active_tab.filepath}")
            except Exception as e:
                self.log_output(f"[ERROR] Save failed: {e}")
        else:
            self.save_as()

    def save_as(self):
        active_tab = self.get_active_tab()
        if not active_tab:
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            active_tab.filepath = filepath

            old_name = self.tab_view.get()
            new_name = os.path.basename(filepath)
            self.tab_view.tab(old_name, text=new_name)

            self.tabs[new_name] = self.tabs.pop(old_name)

            self.save_file()
            self.file_label.configure(text=f"File: {filepath}")

    def close_current_tab(self):
        active_tab = self.get_active_tab()
        if not active_tab:
            return

        if active_tab.unsaved:
            res = messagebox.askyesnocancel("Save?", f"Do you want to save changes to {active_tab.filepath or 'Untitled'}?")
            if res is None:
                return
            if res:
                self.save_file()

        tab_name = self.tab_view.get()
        self.tab_view.delete(tab_name)
        del self.tabs[tab_name]

        if not self.tabs:
            self.new_file()

    # ========== CODE EXECUTION ==========
    def run_python(self):
        active_tab = self.get_active_tab()
        if not active_tab:
            return

        if not active_tab.filepath:
            self.save_as()
            if not active_tab.filepath:
                return
        else:
            if active_tab.unsaved:
                self.save_file()

        self.log_output(f"\n>>> Running: {os.path.basename(active_tab.filepath)}")

        def run():
            try:
                result = subprocess.run(
                    ["python", active_tab.filepath],
                    capture_output=True, text=True, timeout=10
                )
                self.root.after(0, lambda: self.log_output(result.stdout))
                if result.stderr:
                    self.root.after(0, lambda: self.log_output(f"ERROR:\n{result.stderr}"))
            except Exception as e:
                self.root.after(0, lambda: self.log_output(f"[EXCEPTION] {e}"))

        threading.Thread(target=run, daemon=True).start()

    def run_selection(self):
        active_tab = self.get_active_tab()
        if not active_tab:
            return

        try:
            selected = active_tab.text_editor.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected.strip():
                self.log_output(f"\n>>> Running selection...")
                exec(selected, globals())
                self.log_output("[DONE] Selection executed")
        except:
            self.log_output("[ERROR] No text selected or execution failed")

    def debug_python(self):
        active_tab = self.get_active_tab()
        if not active_tab or not active_tab.filepath:
            self.log_output("[ERROR] Please save the file before debugging.")
            return

        self.log_output(f"\n>>> Debugging: {os.path.basename(active_tab.filepath)}")

        self.debugger_process = subprocess.Popen(
            ["python", "-m", "pdb", active_tab.filepath],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, universal_newlines=True
        )

        threading.Thread(target=self.handle_debugger_output, args=(self.debugger_process.stdout,), daemon=True).start()
        threading.Thread(target=self.handle_debugger_output, args=(self.debugger_process.stderr,), daemon=True).start()
        threading.Thread(target=self.handle_debugger_input, daemon=True).start()

    def handle_debugger_input(self):
        while self.debugger_process and self.debugger_process.poll() is None:
            try:
                cmd = self.debugger_input_queue.get(timeout=0.1)
                if self.debugger_process.stdin:
                    self.debugger_process.stdin.write(cmd)
                    self.debugger_process.stdin.flush()
            except queue.Empty:
                continue

    def handle_debugger_output(self, stream):
        for line in iter(stream.readline, ''):
            self.log_output(line.strip())
        stream.close()

    # ========== UI CONTROLS ==========
    def toggle_explorer(self):
        if self.explorer_frame.winfo_ismapped():
            self.explorer_frame.pack_forget()
        else:
            self.explorer_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))

    def toggle_terminal(self):
        if self.output_frame.winfo_ismapped():
            self.output_frame.pack_forget()
        else:
            self.output_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 8))

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        mode = "dark" if self.is_dark else "light"
        ctk.set_appearance_mode(mode)
        self.theme_btn.configure(text=self.icons.get("theme_light") if not self.is_dark else self.icons.get("theme_dark"))
        self.update_theme_colors(mode)

    def set_theme(self, mode):
        self.is_dark = (mode == "dark")
        ctk.set_appearance_mode(mode)
        self.theme_btn.configure(text=self.icons.get("theme_light") if self.is_dark else self.icons.get("theme_dark"))
        self.update_theme_colors(mode)

    def update_theme_colors(self, mode):
        bg_editor = "#1e1e1e" if mode == "dark" else "#ffffff"
        fg_text = "#d4d4d4" if mode == "dark" else "#000000"
        bg_lines = "#252526" if mode == "dark" else "#f0f0f0"
        fg_lines = "#858585" if mode == "dark" else "#666666"

        for tab in self.tabs.values():
            tab.text_editor.config(bg=bg_editor, fg=fg_text)
            tab.line_numbers.config(bg=bg_lines, fg=fg_lines)

        self.terminal_output.config(bg="#0c0c0c" if mode == "dark" else "#f5f5f5",
                                    fg="#cccccc" if mode == "dark" else "#333333")
        self.explorer_text.config(bg="#2b2b2b" if mode == "dark" else "#f0f0f0",
                                  fg="white" if mode == "dark" else "black")

    def apply_syntax_highlighting(self):
        active_tab = self.get_active_tab()
        if not active_tab:
            return

        editor = active_tab.text_editor

        for tag in editor.tag_names():
            if tag not in ["sel", "highlight"]:
                editor.tag_remove(tag, "1.0", "end")

        editor.tag_configure("keyword", foreground="#569CD6")
        editor.tag_configure("string", foreground="#CE9178")
        editor.tag_configure("comment", foreground="#6A9955")
        editor.tag_configure("function", foreground="#DCDCAA")

        content = editor.get("1.0", "end-1c")
        lines = content.split('\n')

        for i, line in enumerate(lines, start=1):
            if '#' in line:
                start_idx = line.index('#')
                editor.tag_add("comment", f"{i}.{start_idx}", f"{i}.end")

            in_string = False
            string_char = None
            for j, ch in enumerate(line):
                if ch in ('"', "'"):
                    if not in_string:
                        in_string = True
                        string_char = ch
                        start = j
                    elif ch == string_char:
                        in_string = False
                        editor.tag_add("string", f"{i}.{start}", f"{i}.{j+1}")

            keywords = ["def", "class", "import", "from", "if", "else", "elif",
                        "for", "while", "return", "try", "except", "with", "as",
                        "True", "False", "None", "and", "or", "not", "in", "is"]
            for kw in keywords:
                idx = 0
                while True:
                    idx = line.find(kw, idx)
                    if idx == -1:
                        break
                    if (idx == 0 or not line[idx-1].isalnum()) and \
                       (idx + len(kw) == len(line) or not line[idx+len(kw)].isalnum()):
                        editor.tag_add("keyword", f"{i}.{idx}", f"{i}.{idx+len(kw)}")
                    idx += len(kw)

    def log_output(self, message):
        self.terminal_output.config(state='normal')
        self.terminal_output.insert('end', str(message) + '\n')
        self.terminal_output.see('end')
        self.terminal_output.config(state='disabled')

    def clear_output(self):
        self.terminal_output.config(state='normal')
        self.terminal_output.delete('1.0', 'end')
        self.terminal_output.config(state='disabled')

    def show_about(self):
        about = ctk.CTkToplevel(self.root)
        about.title("About Mini Eclipse")
        about.geometry("400x300")
        about.resizable(False, False)

        ctk.CTkLabel(about, text="🚀", font=("Segoe UI", 48)).pack(pady=(20, 10))
        ctk.CTkLabel(about, text="Mini Eclipse IDE", font=("Segoe UI", 24, "bold")).pack()
        ctk.CTkLabel(about, text="A lightweight Python IDE", font=("Segoe UI", 14)).pack(pady=10)
        ctk.CTkLabel(about, text="Built with CustomTkinter", font=("Segoe UI", 12)).pack()
        ctk.CTkLabel(about, text="Version 0.3.0", font=("Segoe UI", 10)).pack(pady=20)

        ctk.CTkButton(about, text="Close", command=about.destroy).pack(pady=20)

# ============================================
# 5. MAIN LAUNCH (FIXED)
# ============================================
def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("1300x900")

    def start_app():
        MiniEclipseIDE(root)

    SplashScreen(root, start_app)
    root.mainloop()


if __name__ == "__main__":
    main()