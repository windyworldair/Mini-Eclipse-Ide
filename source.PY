import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, Menu
import subprocess
import os
import time

# ============================================
# 1. SPLASH SCREEN (FIXED – single root)
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
# 2. ICON MANAGER
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
# 3. MAIN IDE
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
        self.current_file = None
        self.folder_path = None
        
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
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=lambda: self.text_editor.event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=lambda: self.text_editor.event_generate("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X", command=lambda: self.text_editor.event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=lambda: self.text_editor.event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=lambda: self.text_editor.event_generate("<<Paste>>"))
        
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
        self.file_label = ctk.CTkLabel(toolbar_frame, text="Untitled", 
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
        
        # Initial update
        self.update_line_numbers()
        
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
        editor_panel = ctk.CTkFrame(parent, corner_radius=8, height=500)  # ← 500 instead of 400
        editor_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        editor_panel.pack_propagate(False)
        
        # Header
        editor_header = ctk.CTkFrame(editor_panel, height=30, fg_color="transparent")
        editor_header.pack(fill=tk.X, padx=10, pady=(10, 0))
        ctk.CTkLabel(editor_header, text="EDITOR", 
                     font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        
        # Editor with line numbers
        editor_container = tk.Frame(editor_panel, bg="#252526")
        editor_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Line numbers
        self.line_numbers = tk.Text(editor_container, width=4, padx=5, pady=5, 
                                    bg="#252526", fg="#858585", state='disabled', 
                                    bd=0, font=("Consolas", 13))
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # Main editor
        self.text_editor = tk.Text(
            editor_container, bg="#1e1e1e", fg="#d4d4d4", bd=0,
            insertbackground="white", font=("Consolas", 13),
            wrap=tk.NONE, undo=True, padx=10, pady=5
        )
        self.text_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Sync scroll
        def sync_scroll(*args):
            self.line_numbers.yview_moveto(args[0])
            self.text_editor.yview_moveto(args[0])
        
        scrollbar = tk.Scrollbar(editor_container, command=sync_scroll)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_editor.config(yscrollcommand=scrollbar.set)
        self.line_numbers.config(yscrollcommand=scrollbar.set)
        
        # Sample code
        sample = '''# Welcome to Mini Eclipse
print("Hello, World!")

def factorial(n):
    if n <= 1:
        return 1
    else:
        return n * factorial(n - 1)

if __name__ == "__main__":
    result = factorial(5)
    print(f"5! = {result}")'''
        self.text_editor.insert('1.0', sample)
        self.apply_syntax_highlighting()
        
        # Bind events
        self.text_editor.bind('<KeyRelease>', lambda e: self.update_line_numbers())
        self.text_editor.bind('<MouseWheel>', lambda e: self.update_line_numbers())
        
        # Tab width
        self.text_editor.config(tabs=4)
    
    def update_line_numbers(self, event=None):
        lines = self.text_editor.get('1.0', 'end').count('\n')
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', 'end')
        self.line_numbers.insert('1.0', '\n'.join(str(i) for i in range(1, lines + 1)))
        self.line_numbers.config(state='disabled')
        self.apply_syntax_highlighting()
    
    def setup_terminal(self):
        self.output_frame = ctk.CTkFrame(self.root, corner_radius=8)
        self.output_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False, padx=8, pady=(0, 8))
        self.output_frame.configure(height=250)  # set a reasonable terminal height
        
        # Header
        output_header = ctk.CTkFrame(self.output_frame, height=30, fg_color="transparent")
        output_header.pack(fill=tk.X, padx=10, pady=(8, 0))
        ctk.CTkLabel(output_header, text="OUTPUT", 
                     font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        
        ctk.CTkButton(output_header, text="Clear", width=60, height=24,
                      command=self.clear_output).pack(side=tk.RIGHT, padx=5)
        
        # Terminal text
        self.terminal_output = tk.Text(
            self.output_frame, bg="#0c0c0c", fg="#cccccc", bd=0,
            height=15, font=("Consolas", 11), padx=10, pady=5
        )
        self.terminal_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.terminal_output.insert('1.0', ">>> Mini Eclipse Terminal - Ready\n")
        self.terminal_output.config(state='disabled')
        
        # Scrollbar
        t_scroll = tk.Scrollbar(self.output_frame, command=self.terminal_output.yview)
        t_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.terminal_output.config(yscrollcommand=t_scroll.set)
    
    # ========== FILE OPERATIONS ==========
    def new_file(self):
        self.text_editor.delete('1.0', 'end')
        self.current_file = None
        self.file_label.configure(text="Untitled")
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
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            self.text_editor.delete('1.0', tk.END)
            self.text_editor.insert('1.0', content)
            self.current_file = filepath
            self.file_label.configure(text=f"File: {os.path.basename(filepath)}")
            self.update_line_numbers()
            self.log_output(f"[INFO] Loaded: {filepath}")
        except Exception as e:
            self.log_output(f"[ERROR] {e}")
    
    def save_file(self):
        if self.current_file:
            try:
                with open(self.current_file, 'w', encoding='utf-8') as f:
                    f.write(self.text_editor.get('1.0', 'end-1c'))
                self.log_output(f"[INFO] Saved: {self.current_file}")
            except Exception as e:
                self.log_output(f"[ERROR] Save failed: {e}")
        else:
            self.save_as()
    
    def save_as(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            self.current_file = filepath
            self.file_label.configure(text=f"File: {os.path.basename(filepath)}")
            self.save_file()
    
    # ========== CODE EXECUTION ==========
    def run_python(self):
        if not self.current_file:
            self.save_as()
            if not self.current_file:
                return
        
        self.log_output(f"\n>>> Running: {os.path.basename(self.current_file)}")
        
        def run():
            try:
                result = subprocess.run(
                    ["python", self.current_file],
                    capture_output=True, text=True, timeout=10
                )
                self.root.after(0, lambda: self.log_output(result.stdout))
                if result.stderr:
                    self.root.after(0, lambda: self.log_output(f"ERROR:\n{result.stderr}"))
            except Exception as e:
                self.root.after(0, lambda: self.log_output(f"[EXCEPTION] {e}"))
        
        # Run in thread (this is safe for subprocess)
        import threading
        threading.Thread(target=run, daemon=True).start()
    
    def run_selection(self):
        try:
            selected = self.text_editor.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected.strip():
                self.log_output(f"\n>>> Running selection...")
                exec(selected, globals())
                self.log_output("[DONE] Selection executed")
        except:
            self.log_output("[ERROR] No text selected or execution failed")
    
    def debug_python(self):
        self.log_output("[DEBUG] Debug mode placeholder - Add breakpoints manually.")
    
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
        self.theme_btn.configure(text=self.icons.get("theme_light") if self.is_dark else self.icons.get("theme_dark"))
        self.update_theme_colors(mode)
    
    def set_theme(self, mode):
        self.is_dark = (mode == "dark")
        ctk.set_appearance_mode(mode)
        self.theme_btn.configure(text=self.icons.get("theme_light") if self.is_dark else self.icons.get("theme_dark"))
        self.update_theme_colors(mode)
    
    def update_theme_colors(self, mode):
        if mode == "dark":
            self.text_editor.config(bg="#1e1e1e", fg="#d4d4d4")
            self.line_numbers.config(bg="#252526", fg="#858585")
            self.terminal_output.config(bg="#0c0c0c", fg="#cccccc")
            self.explorer_text.config(bg="#2b2b2b", fg="white")
        else:
            self.text_editor.config(bg="#ffffff", fg="#000000")
            self.line_numbers.config(bg="#f0f0f0", fg="#666666")
            self.terminal_output.config(bg="#f5f5f5", fg="#333333")
            self.explorer_text.config(bg="#f0f0f0", fg="black")
    
    def apply_syntax_highlighting(self):
        # Remove old tags
        for tag in self.text_editor.tag_names():
            if tag not in ["sel", "highlight"]:
                self.text_editor.tag_remove(tag, "1.0", "end")
        
        # Configure tags
        self.text_editor.tag_configure("keyword", foreground="#569CD6")
        self.text_editor.tag_configure("string", foreground="#CE9178")
        self.text_editor.tag_configure("comment", foreground="#6A9955")
        self.text_editor.tag_configure("function", foreground="#DCDCAA")
        
        content = self.text_editor.get("1.0", "end-1c")
        lines = content.split('\n')
        
        for i, line in enumerate(lines, start=1):
            # Comments
            if '#' in line:
                start_idx = line.index('#')
                self.text_editor.tag_add("comment", f"{i}.{start_idx}", f"{i}.end")
            
            # Strings (simple)
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
                        self.text_editor.tag_add("string", f"{i}.{start}", f"{i}.{j+1}")
            
            # Keywords
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
                        self.text_editor.tag_add("keyword", f"{i}.{idx}", f"{i}.{idx+len(kw)}")
                    idx += len(kw)
    
    def log_output(self, message):
        self.terminal_output.config(state='normal')
        self.terminal_output.insert('end', message + '\n')
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
        ctk.CTkLabel(about, text="Version 0.1.0", font=("Segoe UI", 10)).pack(pady=20)
        
        ctk.CTkButton(about, text="Close", command=about.destroy).pack(pady=20)

# ============================================
# 4. MAIN LAUNCH (FIXED)
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