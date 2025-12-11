import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, Menu, messagebox
import subprocess
import os
import re
import sys
import threading
import time
import importlib.util
import pkgutil
from queue import Queue, Empty
from pygments.lexers import get_lexer_by_name
from pygments import lex
from pygments.token import Token

# ============================================
# 1. SPLASH SCREEN
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
        self.center_splash()
        root.withdraw()

        ctk.CTkLabel(self.splash, text="🚀", font=("Segoe UI", 48)).pack(pady=(30, 5))
        ctk.CTkLabel(self.splash, text="Ball Python IDE", font=("Segoe UI", 24, "bold")).pack()
        ctk.CTkLabel(self.splash, text="Upgraded Edition", font=("Segoe UI", 12)).pack(pady=(0, 20))

        self.progress = ctk.CTkProgressBar(self.splash, width=300, height=16)
        self.progress.pack()
        self.progress.set(0)
        self.status_label = ctk.CTkLabel(self.splash, text="Initializing...")
        self.status_label.pack(pady=15)
        self.start_loading()

    def center_splash(self):
        self.splash.update_idletasks()
        x = (self.root.winfo_screenwidth() - 400) // 2
        y = (self.root.winfo_screenheight() - 250) // 2
        self.splash.geometry(f"400x250+{x}+{y}")

    def start_loading(self):
        for i in range(101):
            self.progress.set(i / 100)
            self.status_label.configure(text=f"Loading components... {i}%")
            self.splash.update_idletasks()
            time.sleep(0.01)
        self.splash.after(300, self.finish_loading)

    def finish_loading(self):
        self.splash.destroy()
        self.root.deiconify()
        self.on_complete()

# ============================================
# 2. ICON MANAGER
# ============================================
class IconManager:
    def __init__(self):
        self.icons = {"py": "🐍", "folder": "📁", "file": "📄", "run": "▶", "debug": "🐞",
                      "explorer": "📁", "theme_dark": "🌙", "theme_light": "☀️", "terminal": "📟"}
    def get(self, key):
        return self.icons.get(key, "📄")

# ============================================
# 3. AUTOCOMPLETE MANAGER (NEW)
# ============================================
class AutocompleteManager:
    def __init__(self, editor_widget):
        self.editor = editor_widget
        self.listbox = None
        self.words = []

    def show_autocomplete(self, event=None):
        if self.listbox: self.listbox.destroy()

        cursor_pos = self.editor.index(tk.INSERT)
        line_content = self.editor.get(f"{cursor_pos.split('.')[0]}.0", cursor_pos)
        current_word = re.split(r'\W+', line_content)[-1]

        if len(current_word) < 2: return

        # Simple word gathering from the editor content
        text_content = self.editor.get("1.0", "end")
        self.words = sorted(list(set(re.findall(r'\w+', text_content))))

        suggestions = [w for w in self.words if w.startswith(current_word) and w != current_word]

        if not suggestions: return

        x, y, _, _ = self.editor.bbox(tk.INSERT)
        self.listbox = tk.Listbox(self.editor, bg="#3A3A3A", fg="white", selectbackground="#569CD6")
        self.listbox.place(x=x, y=y + 20)
        self.listbox.bind("<Double-Button-1>", self.insert_word)
        self.listbox.bind("<Return>", self.insert_word)

        for s in suggestions[:8]: # Limit suggestions
            self.listbox.insert(tk.END, s)

    def insert_word(self, event=None):
        if not self.listbox: return
        selected = self.listbox.get(self.listbox.curselection())

        cursor_pos = self.editor.index(tk.INSERT)
        line_start = f"{cursor_pos.split('.')[0]}.0"
        line_content = self.editor.get(line_start, cursor_pos)

        last_word_len = len(re.split(r'\W+', line_content)[-1])

        self.editor.delete(f"insert-{last_word_len}c", "insert")
        self.editor.insert(tk.INSERT, selected)
        self.listbox.destroy()
        self.listbox = None

    def hide_autocomplete(self, event=None):
        if self.listbox:
            self.listbox.destroy()
            self.listbox = None

# ============================================
# 4. EDITOR FRAME (NEW)
# ============================================
class Editor(ctk.CTkFrame):
    def __init__(self, master, filepath=None):
        super().__init__(master, fg_color="transparent")
        self.filepath = filepath
        self.has_unsaved_changes = False

        editor_container = tk.Frame(self, bg="#252526")
        editor_container.pack(fill=tk.BOTH, expand=True)

        self.line_numbers = tk.Text(editor_container, width=4, padx=5, pady=5, bg="#252526",
                                    fg="#858585", state='disabled', bd=0, font=("Consolas", 13))
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        self.text_editor = tk.Text(editor_container, bg="#1e1e1e", fg="#d4d4d4", bd=0,
                                   insertbackground="white", font=("Consolas", 13),
                                   wrap=tk.NONE, undo=True, padx=10, pady=5)
        self.text_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_editor.config(tabs=4)

        scrollbar = tk.Scrollbar(editor_container, command=self._sync_scroll)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_editor.config(yscrollcommand=scrollbar.set)
        self.line_numbers.config(yscrollcommand=scrollbar.set)

        self.text_editor.bind('<<Modified>>', self._on_text_modified)
        self.text_editor.bind('<KeyRelease>', self.on_key_release)
        self.text_editor.bind("<FocusOut>", lambda e: self.autocomplete.hide_autocomplete())
        self.text_editor.bind("<Control-space>", self.autocomplete.show_autocomplete)

        self.autocomplete = AutocompleteManager(self.text_editor)
        self.lexer = get_lexer_by_name("python")
        self._setup_highlighting_tags()

        self.update_line_numbers()

    def _setup_highlighting_tags(self):
        self.text_editor.tag_configure("Token.Keyword", foreground="#569CD6")
        self.text_editor.tag_configure("Token.Name.Function", foreground="#DCDCAA")
        self.text_editor.tag_configure("Token.String", foreground="#CE9178")
        self.text_editor.tag_configure("Token.Comment", foreground="#6A9955")
        self.text_editor.tag_configure("Token.Operator", foreground="#D4D4D4")
        self.text_editor.tag_configure("Token.Number", foreground="#B5CEA8")

    def _apply_syntax_highlighting(self):
        code = self.get_content()
        self.text_editor.mark_set("range_start", "1.0")

        for tag in self.text_editor.tag_names():
            if tag.startswith("Token."):
                self.text_editor.tag_remove(tag, "1.0", "end")

        for token, content in lex(code, self.lexer):
            self.text_editor.mark_set("range_end", f"range_start + {len(content)}c")
            self.text_editor.tag_add(str(token), "range_start", "range_end")
            self.text_editor.mark_set("range_start", "range_end")

    def _sync_scroll(self, *args):
        self.line_numbers.yview_moveto(args[0])
        self.text_editor.yview_moveto(args[0])

    def _on_text_modified(self, event=None):
        if not self.has_unsaved_changes:
             self.has_unsaved_changes = True
             # master is the tab, master.master is the tabview. This is brittle.
             # A better way would be to pass a callback.
             self.master.master.update_tab_title(self)
        self.text_editor.edit_modified(False)
        # Schedule highlighting to run after Tkinter has processed the keystroke
        self.after(1, self._apply_syntax_highlighting)

    def on_key_release(self, event=None):
        self.update_line_numbers()
        self._apply_syntax_highlighting()

    def get_content(self):
        return self.text_editor.get('1.0', 'end-1c')

    def set_content(self, content):
        self.text_editor.delete('1.0', 'end')
        self.text_editor.insert('1.0', content)
        self.text_editor.edit_modified(False)
        self.has_unsaved_changes = False
        self.master.master.update_tab_title(self)
        self.update_line_numbers()

    def update_line_numbers(self, event=None):
        lines = self.text_editor.get('1.0', 'end-1c').count('\n') + 1
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', 'end')
        self.line_numbers.insert('1.0', '\n'.join(str(i) for i in range(1, lines + 1)))
        self.line_numbers.config(state='disabled')

# ============================================
# 4. MAIN IDE (REFACTORED)
# ============================================
class MiniEclipseIDE:
    def __init__(self, root):
        self.root = root
        self.root.title("Ball Python IDE")
        self.root.geometry("1300x900")
        self.center_window()

        self.icons = IconManager()
        self.is_dark = True
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.folder_path = None
        self.editors = {}
        self.tab_count = 0
        self.debugger_process = None
        self.debugger_input_queue = None
        self.debugger_output_queue = None

        self.setup_ui()
        self.new_file()
        self.load_plugins()

    def center_window(self):
        self.root.update_idletasks()
        width, height = self.root.winfo_width(), self.root.winfo_height()
        x = (self.root.winfo_screenwidth() - width) // 2
        y = (self.root.winfo_screenheight() - height) // 2
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_ui(self):
        self.setup_menu()
        self.setup_toolbar()
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.setup_explorer(main_container)
        self.setup_editor_tabs(main_container)
        self.setup_terminal()
        self.bind_shortcuts()

    def setup_menu(self):
        self.menubar = Menu(self.root, font=("Segoe UI", 10))
        self.root.config(menu=self.menubar)

        # File Menu
        file_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As...", accelerator="Ctrl+Shift+S", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Close Tab", accelerator="Ctrl+W", command=self.close_current_tab)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Edit Menu (targets current editor)
        edit_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=lambda: self.get_current_editor().text_editor.event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=lambda: self.get_current_editor().text_editor.event_generate("<<Redo>>"))

        # Run Menu
        run_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(label="Run File", accelerator="F5", command=self.run_python)
        run_menu.add_command(label="Debug File", accelerator="F6", command=self.debug_python)
        run_menu.add_command(label="Stop Debugger", command=self.stop_debugger)

        # Plugins Menu (placeholder)
        self.plugin_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Plugins", menu=self.plugin_menu)
        self.plugin_menu.add_command(label="No plugins loaded", state="disabled")

    def setup_toolbar(self):
        toolbar_frame = ctk.CTkFrame(self.root, height=42, fg_color="transparent")
        toolbar_frame.pack(side=tk.TOP, fill=tk.X, padx=8, pady=3)
        btn_style = {"width": 38, "height": 34, "corner_radius": 6, "fg_color": "transparent",
                     "hover_color": ("#e0e0e0", "#3a3a3a"), "text_color": ("black", "white"),
                     "font": ("Segoe UI Emoji", 18)}
        ctk.CTkButton(toolbar_frame, text=self.icons.get("run"), command=self.run_python, **btn_style).pack(side=tk.LEFT, padx=3)
        ctk.CTkButton(toolbar_frame, text=self.icons.get("debug"), command=self.debug_python, **btn_style).pack(side=tk.LEFT, padx=3)

    def setup_explorer(self, parent):
        self.explorer_frame = ctk.CTkFrame(parent, width=230, corner_radius=8)
        self.explorer_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        ctk.CTkButton(self.explorer_frame, text="Open Folder", command=self.open_folder).pack(fill=tk.X, padx=10, pady=10)
        self.explorer_text = tk.Text(self.explorer_frame, bg="#2b2b2b", fg="white", bd=0, font=("Segoe UI", 11), state='disabled')
        self.explorer_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        self.explorer_text.bind("<Double-Button-1>", self.on_explorer_double_click)

    def setup_editor_tabs(self, parent):
        editor_panel = ctk.CTkFrame(parent, corner_radius=8)
        editor_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tab_view = ctk.CTkTabview(editor_panel, fg_color="#252526")
        self.tab_view.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        # Hack to remove the default tab
        self.tab_view._segmented_button.grid_forget()
        self.tab_view._segmented_button = ctk.CTkSegmentedButton(self.tab_view, corner_radius=4,
                                                                 command=self.tab_view.set,
                                                                 font=("Segoe UI", 11))
        self.tab_view._segmented_button.grid(row=0, column=0, columnspan=1, padx=2, pady=2, sticky="ew")


    def setup_terminal(self):
        self.output_frame = ctk.CTkFrame(self.root, corner_radius=8, height=250)
        self.output_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False, padx=8, pady=(0, 8))
        self.output_frame.pack_propagate(False)
        self.terminal_output = tk.Text(self.output_frame, bg="#0c0c0c", fg="#cccccc", bd=0, font=("Consolas", 11))
        self.terminal_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.terminal_output.bind("<Return>", self.handle_terminal_input)
        self.log_output(">>> Ball Python IDE Terminal - Ready")

    def bind_shortcuts(self):
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-Shift-s>", lambda e: self.save_as())
        self.root.bind("<Control-w>", lambda e: self.close_current_tab())
        self.root.bind("<F5>", lambda e: self.run_python())
        self.root.bind("<F6>", lambda e: self.debug_python())

    def get_current_editor(self):
        tab_name = self.tab_view.get()
        return self.editors.get(tab_name) if tab_name else None

    def update_tab_title(self, editor):
        current_name = None
        for name, ed in self.editors.items():
            if ed == editor:
                current_name = name
                break
        if not current_name: return

        base_name = os.path.basename(editor.filepath) if editor.filepath else current_name.split('*')[0]
        new_name = f"{base_name}*" if editor.has_unsaved_changes else base_name

        if current_name != new_name:
            self.tab_view._segmented_button.rename(current_name, new_name)
            self.editors[new_name] = self.editors.pop(current_name)
            if self.tab_view.get() == current_name:
                self.tab_view.set(new_name)


    def new_file(self):
        self.tab_count += 1
        tab_name = f"Untitled-{self.tab_count}"
        self.tab_view.add(tab_name)
        self.tab_view.set(tab_name)
        editor = Editor(self.tab_view.tab(tab_name))
        editor.pack(fill=tk.BOTH, expand=True)
        self.editors[tab_name] = editor
        editor.text_editor.focus_set()

    def open_file(self, filepath=None):
        if not filepath:
            filepath = filedialog.askopenfilename()
        if not filepath: return

        for editor in self.editors.values():
            if editor.filepath == filepath:
                for name, ed in self.editors.items():
                    if ed == editor:
                        self.tab_view.set(name)
                        return
        try:
            with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
            filename = os.path.basename(filepath)
            self.tab_view.add(filename)
            editor = Editor(self.tab_view.tab(filename), filepath=filepath)
            editor.pack(fill=tk.BOTH, expand=True)
            editor.set_content(content)
            self.editors[filename] = editor
            self.tab_view.set(filename)
            self.log_output(f"[INFO] Opened: {filepath}")
        except Exception as e:
            self.log_output(f"[ERROR] Failed to open file: {e}")

    def close_current_tab(self):
        editor = self.get_current_editor()
        if not editor: return

        if editor.has_unsaved_changes:
            response = messagebox.askyesnocancel("Save?", f"You have unsaved changes. Save before closing?")
            if response is None: return # Cancel
            if response: self.save_file() # Yes

        tab_name = self.tab_view.get()
        self.tab_view.delete(tab_name)
        del self.editors[tab_name]

    def save_file(self):
        editor = self.get_current_editor()
        if not editor: return
        if editor.filepath:
            try:
                with open(editor.filepath, 'w', encoding='utf-8') as f: f.write(editor.get_content())
                self.log_output(f"[INFO] Saved: {editor.filepath}")
                editor.has_unsaved_changes = False
                self.update_tab_title(editor)
            except Exception as e:
                self.log_output(f"[ERROR] Save failed: {e}")
        else:
            self.save_as()

    def save_as(self):
        editor = self.get_current_editor()
        if not editor: return
        filepath = filedialog.asksaveasfilename(defaultextension=".py")
        if filepath:
            old_tab_name = self.tab_view.get()
            editor.filepath = filepath
            self.save_file()
            # Rename tab logic
            new_tab_name = os.path.basename(filepath)
            self.tab_view._segmented_button.rename(old_tab_name, new_tab_name)
            self.editors[new_tab_name] = self.editors.pop(old_tab_name)
            self.tab_view.set(new_tab_name)


    def run_python(self):
        editor = self.get_current_editor()
        if not editor: return
        if not editor.filepath:
            self.save_as()
            if not editor.filepath: return
        else: self.save_file()

        self.log_output(f"\n>>> Running {os.path.basename(editor.filepath)}...")
        try:
            result = subprocess.run([sys.executable, editor.filepath], capture_output=True, text=True, timeout=10)
            if result.stdout: self.log_output(result.stdout)
            if result.stderr: self.log_output(f"ERROR:\n{result.stderr}")
        except Exception as e:
            self.log_output(f"[EXCEPTION] {e}")

    def debug_python(self):
        editor = self.get_current_editor()
        if not editor or not editor.filepath:
            messagebox.showerror("Error", "Save the file before debugging.")
            return

        self.log_output(f"\n>>> Starting debugger for {os.path.basename(editor.filepath)}...")
        self.terminal_output.config(state='normal')

        self.debugger_input_queue = Queue()
        self.debugger_output_queue = Queue()

        def debug_thread():
            self.debugger_process = subprocess.Popen(
                [sys.executable, "-m", "pdb", editor.filepath],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1, universal_newlines=True
            )
            # Thread to read debugger output
            threading.Thread(target=self._read_debugger_output, daemon=True).start()

            while self.debugger_process.poll() is None:
                try:
                    cmd = self.debugger_input_queue.get(timeout=0.1)
                    if cmd is None: break # Sentinel value to stop
                    self.debugger_process.stdin.write(cmd + '\n')
                    self.debugger_process.stdin.flush()
                except Empty:
                    continue
            self.stop_debugger()

        threading.Thread(target=debug_thread, daemon=True).start()

    def _read_debugger_output(self):
        for line in iter(self.debugger_process.stdout.readline, ''):
            self.log_output(line)
        for line in iter(self.debugger_process.stderr.readline, ''):
            self.log_output(line)

    def stop_debugger(self):
        if self.debugger_process:
            if self.debugger_process.poll() is None:
                self.debugger_process.kill()
            self.debugger_process = None
            self.log_output("\n>>> Debugger stopped.")
        self.terminal_output.config(state='disabled')


    def on_explorer_double_click(self, event):
        index = self.explorer_text.index(f"@{event.x},{event.y}")
        line = int(index.split('.')[0])
        # This is a simplification. A real implementation would need a more robust way
        # to map text lines to file paths.
        try:
            path = self.explorer_text.get(f"{line}.0", f"{line}.end").strip().split(" ")[-1]
            if self.folder_path and os.path.isfile(os.path.join(self.folder_path, path)):
                 self.open_file(os.path.join(self.folder_path, path))
        except:
             pass

    def open_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path = folder
            self.refresh_explorer()

    def refresh_explorer(self):
        self.explorer_text.config(state='normal')
        self.explorer_text.delete('1.0', 'end')
        if not self.folder_path: return

        self.explorer_text.insert('end', f"{self.icons.get('folder')} {os.path.basename(self.folder_path)}\n")
        for item in sorted(os.listdir(self.folder_path)):
            full_path = os.path.join(self.folder_path, item)
            icon = self.icons.get('folder') if os.path.isdir(full_path) else self.icons.get('py') if item.endswith(".py") else self.icons.get('file')
            self.explorer_text.insert('end', f"  {icon} {item}\n")
        self.explorer_text.config(state='disabled')

    def log_output(self, message):
        self.terminal_output.config(state='normal')
        self.terminal_output.insert('end', str(message).strip() + '\n')
        self.terminal_output.see('end')
        if not self.debugger_process:
             self.terminal_output.config(state='disabled')

    def handle_terminal_input(self, event=None):
        if self.debugger_process:
            command = self.terminal_output.get("insert linestart", "insert")
            self.debugger_input_queue.put(command)
        return "break"

    def load_plugins(self):
        plugin_dir = "plugins"
        if not os.path.exists(plugin_dir):
            os.makedirs(plugin_dir)

        # Clear existing plugin menu
        self.plugin_menu.delete(0, tk.END)

        for finder, name, ispkg in pkgutil.iter_modules([plugin_dir]):
            spec = finder.find_spec(name)
            if spec:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "register"):
                    module.register(self)
                    self.log_output(f"[INFO] Loaded plugin: {name}")

# ============================================
# 5. MAIN LAUNCH
# ============================================
def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()

    def start_app():
        MiniEclipseIDE(root)

    SplashScreen(root, start_app)
    root.mainloop()

if __name__ == "__main__":
    main()