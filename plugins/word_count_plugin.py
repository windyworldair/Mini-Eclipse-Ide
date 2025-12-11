import tkinter as tk
from tkinter import messagebox

class WordCountPlugin:
    def __init__(self, ide_instance):
        self.ide = ide_instance

    def run(self):
        editor = self.ide.get_current_editor()
        if editor:
            content = editor.get_content()
            word_count = len(content.split())
            messagebox.showinfo("Word Count", f"The current file has {word_count} words.")

def register(ide_instance):
    plugin = WordCountPlugin(ide_instance)
    ide_instance.plugin_menu.add_command(label="Word Count", command=plugin.run)
