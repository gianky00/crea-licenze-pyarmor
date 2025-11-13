import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
import shutil
import os
import glob
import queue
import sys
import tempfile
import re
import datetime
import time
import pathlib
import shlex
import urllib.request
import zipfile
import traceback # Importato per logging errori
import fnmatch # Importato per la copia degli asset
import customtkinter as ctk
from database import Database

class ObfuscatorApp(ctk.CTk):
    def __init__(self, db_connection):
        super().__init__()
        self.db = db_connection
        self.title("General Obfuscator and License Manager")
        self.after(0, lambda: self.state('zoomed'))

        # Variabili per i percorsi e dati
        self.source_path = tk.StringVar()
        self.destination_path = tk.StringVar()
        self.license_path = tk.StringVar()
        self.requirements_path = tk.StringVar()

        self.obfuscation_queue = queue.Queue()
        self.license_queue = queue.Queue()

        self.user_data_map = {}
        self.selected_license_id = tk.StringVar()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        # Creazione del Notebook per le schede
        self.notebook = ctk.CTkTabview(self)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Creazione dei frame per le schede
        self.notebook.add('Obfuscator')
        self.notebook.add('License Manager')
        self.notebook.add("Gestione Utenze")
        self.notebook.add("Storico Licenze")

        self.obfuscator_tab = self.notebook.tab('Obfuscator')
        self.license_tab = self.notebook.tab('License Manager')
        self.user_management_tab = self.notebook.tab("Gestione Utenze")
        self.license_history_tab = self.notebook.tab("Storico Licenze")


        self.create_obfuscator_tab()
        self.create_license_tab()
        self.create_user_management_tab()
        self.create_license_history_tab()
        self._refresh_all_user_views()

    def create_license_tab(self):
        # Variabili per la generazione licenza
        self.expiry_date = tk.StringVar()
        self.device_id = tk.StringVar()
        self.selected_user_id_for_license = None

        input_frame = ctk.CTkFrame(self.license_tab, fg_color="transparent")
        input_frame.pack(fill='x', padx=20, pady=(20,10))
        input_frame.grid_columnconfigure(1, weight=1)

        # User Selection Dropdown
        ctk.CTkLabel(input_frame, text="Seleziona Utenza:").grid(row=0, column=0, sticky='w', padx=5, pady=10)
        self.license_user_dropdown_var = ctk.StringVar(value="Nessun utente selezionato")
        self.license_user_dropdown = ctk.CTkOptionMenu(input_frame, variable=self.license_user_dropdown_var, values=[], command=self._on_license_user_selected)
        self.license_user_dropdown.grid(row=0, column=1, columnspan=2, sticky='ew', padx=5, pady=10)

        # Expiry Date
        ctk.CTkLabel(input_frame, text="Data di Scadenza (YYYY-MM-DD):").grid(row=1, column=0, sticky='w', padx=5, pady=10)
        self.expiry_entry = ctk.CTkEntry(input_frame, textvariable=self.expiry_date)
        self.expiry_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=10)
        self.two_months_button = ctk.CTkButton(input_frame, text="Scadenza 2 Mesi", command=self._set_two_months_expiry, width=120)
        self.two_months_button.grid(row=1, column=2, padx=(10, 5), pady=10)

        # Hardware ID
        ctk.CTkLabel(input_frame, text="Serial N. Disco rigido:").grid(row=2, column=0, sticky='w', padx=5, pady=10)
        self.device_id_entry = ctk.CTkEntry(input_frame, textvariable=self.device_id, state="readonly")
        self.device_id_entry.grid(row=2, column=1, columnspan=2, sticky='ew', padx=5, pady=10)

        action_frame = ctk.CTkFrame(self.license_tab, fg_color="transparent")
        action_frame.pack(pady=20, padx=20)

        self.generate_license_button = ctk.CTkButton(action_frame, text="Generate License Key", command=self.start_license_generation)
        self.generate_license_button.pack(side="left", padx=10)

        self.open_folder_button = ctk.CTkButton(action_frame, text="Apri Cartella Licenze", command=self.open_licenses_folder)
        self.open_folder_button.pack(side="left", padx=10)

        license_status_frame = ctk.CTkFrame(self.license_tab, fg_color="transparent")
        license_status_frame.pack(expand=True, fill='both', padx=20, pady=10)
        ctk.CTkLabel(license_status_frame, text="Status:").pack(anchor='w')
        self.license_status_text = ctk.CTkTextbox(license_status_frame, state='disabled', fg_color="black", text_color="white")
        self.license_status_text.pack(expand=True, fill='both')

    def create_obfuscator_tab(self):
        # Frame for source path selection
        source_path_frame = ctk.CTkFrame(self.obfuscator_tab)
        source_path_frame.pack(fill='x', padx=10, pady=(10,0))
        ctk.CTkLabel(source_path_frame, text="Source Folder:").pack(side='left')
        self.source_path_entry = ctk.CTkEntry(source_path_frame, textvariable=self.source_path, state='readonly', width=50)
        self.source_path_entry.pack(side='left', expand=True, fill='x', padx=5)
        self.browse_source_button = ctk.CTkButton(source_path_frame, text="Browse...", command=self.select_source)
        self.browse_source_button.pack(side='left')

        # Frame for destination path selection
        dest_path_frame = ctk.CTkFrame(self.obfuscator_tab)
        dest_path_frame.pack(fill='x', padx=10, pady=(10,0))
        ctk.CTkLabel(dest_path_frame, text="Destination Folder:").pack(side='left')
        self.dest_path_entry = ctk.CTkEntry(dest_path_frame, textvariable=self.destination_path, state='readonly', width=50)
        self.dest_path_entry.pack(side='left', expand=True, fill='x', padx=5)
        self.browse_dest_button = ctk.CTkButton(dest_path_frame, text="Browse...", command=self.select_destination)
        self.browse_dest_button.pack(side='left')

        # Frame for license file selection
        license_path_frame = ctk.CTkFrame(self.obfuscator_tab)
        license_path_frame.pack(fill='x', padx=10, pady=5)
        ctk.CTkLabel(license_path_frame, text="License File (.lic):").pack(side='left')
        self.license_path_entry = ctk.CTkEntry(license_path_frame, textvariable=self.license_path, state='readonly', width=50)
        self.license_path_entry.pack(side='left', expand=True, fill='x', padx=5)
        self.browse_license_button = ctk.CTkButton(license_path_frame, text="Browse...", command=self.select_license_file)
        self.browse_license_button.pack(side='left')

        # Start Button
        self.start_button = ctk.CTkButton(self.obfuscator_tab, text="Start Obfuscation", command=self.start_obfuscation, state='disabled')
        self.start_button.pack(pady=10)

        # Status Area
        status_frame = ctk.CTkFrame(self.obfuscator_tab)
        status_frame.pack(expand=True, fill='both', padx=10, pady=10)
        ctk.CTkLabel(status_frame, text="Status:").pack(anchor='w')
        self.status_text = ctk.CTkTextbox(status_frame, state='disabled', fg_color="black", text_color="white")
        self.status_text.pack(expand=True, fill='both')

    def _update_status(self, message):
        self.status_text.configure(state='normal')
        self.status_text.insert(tk.END, message)
        self.status_text.see(tk.END)
        self.status_text.configure(state='disabled')

    def select_source(self):
        path = filedialog.askdirectory(title="Select Source Folder")
        if path:
            self.source_path.set(path)
            if self.destination_path.get():
                self.start_button.configure(state='normal')
            self._update_status(f"Source set to: {path}\n")

    def select_destination(self):
        path = filedialog.askdirectory(title="Select Destination Folder")
        if path:
            self.destination_path.set(path)
            if self.source_path.get():
                self.start_button.configure(state='normal')
            self._update_status(f"Destination set to: {path}\n")

    def select_license_file(self):
        path = filedialog.askopenfilename(
            title="Select License File",
            filetypes=[("License Files", "*.lic *.rkey"), ("All files", "*.*")]
        )
        if path:
            self.license_path.set(path)
            self._update_status(f"License file set to: {path}\n")

    def check_paths(self):
        if self.source_path.get() and self.destination_path.get():
            self.start_button.configure(state='normal')
        else:
            self.start_button.configure(state='disabled')

    def start_obfuscation(self):
        if not self.source_path.get() or not self.destination_path.get():
            messagebox.showerror("Error", "Please select both a source and destination folder.")
            return

        self.start_button.configure(state='disabled')
        self.browse_source_button.configure(state='disabled')
        self.browse_dest_button.configure(state='disabled')
        self.browse_license_button.configure(state='disabled')
        self.status_text.configure(state='normal')
        self.status_text.delete('1.0', tk.END)
        self.status_text.configure(state='disabled')

        self.process_obfuscation_queue()
        thread = threading.Thread(target=self._run_obfuscation_process)
        thread.daemon = True
        thread.start()

    def process_obfuscation_queue(self):
        try:
            while not self.obfuscation_queue.empty():
                message = self.obfuscation_queue.get_nowait()
                if isinstance(message, tuple) and message[0] == "PROCESS_COMPLETE":
                    self.start_button.configure(state='normal')
                    self.browse_source_button.configure(state='normal')
                    self.browse_dest_button.configure(state='normal')
                    self.browse_license_button.configure(state='normal')
                    build_dir = "build"
                    if os.path.exists(build_dir):
                        shutil.rmtree(build_dir)
                    self._update_status("\nCleanup complete. Ready for next operation.\n")
                else:
                    self._update_status(message)
        finally:
            self.after(100, self.process_obfuscation_queue)

    def on_closing(self):
        self.db.close()
        self.destroy()

    def start_license_generation(self):
        expiry = self.expiry_date.get()
        device_id = self.device_id.get()
        selected_user_name = self.license_user_dropdown_var.get()

        if not self.selected_user_id_for_license:
            messagebox.showerror("Error", "Please select a user.")
            return

        if not expiry or not device_id:
            messagebox.showerror("Error", "Please provide both an expiry date and a device ID.")
            return

        user_id, hwid, dest_path = self.user_data_map[selected_user_name]

        output_folder = dest_path
        if not output_folder or not os.path.isdir(output_folder):
            messagebox.showinfo("Information", "No valid destination path set for this user. Please select a folder.")
            output_folder = filedialog.askdirectory(title="Select a folder to save the license key")
            if not output_folder:
                return

        self.generate_license_button.configure(state='disabled')
        self.license_status_text.configure(state='normal')
        self.license_status_text.delete('1.0', tk.END)
        self.license_status_text.configure(state='disabled')

        # Pass the user ID to the generation process
        thread = threading.Thread(target=self.license_generation_process, args=(expiry, device_id, output_folder, self.selected_user_id_for_license, selected_user_name, self.license_queue))
        thread.daemon = True
        thread.start()
        self.process_license_queue()

    def process_license_queue(self):
        try:
            while True:
                message = self.license_queue.get_nowait()
                if isinstance(message, tuple):
                    if message[0] == "ADD_LICENSE_RECORD":
                        user_id, expiry_date = message[1], message[2]
                        db_success, db_msg = self.db.add_license_record(user_id, expiry_date)
                        if db_success:
                            self._update_license_status("Successfully recorded in history.\n")
                        else:
                            self._update_license_status(f"WARNING: Failed to record in history: {db_msg}\n")
                    elif message[0] == "LICENSE_PROCESS_COMPLETE":
                        self.generate_license_button.configure(state='normal')
                        self._update_license_status("\n--- Ready for next operation. ---\n")
                        self._refresh_license_history()  # Refresh history after generation
                        break
                else:
                    self._update_license_status(message)
        except queue.Empty:
            self.after(100, self.process_license_queue)

    def _update_license_status(self, message):
        self.license_status_text.configure(state='normal')
        self.license_status_text.insert(tk.END, message)
        self.license_status_text.see(tk.END)
        self.license_status_text.configure(state='disabled')

    def create_license_history_tab(self):
        self.license_history_tab.grid_columnconfigure(0, weight=1)
        self.license_history_tab.grid_rowconfigure(1, weight=1)

        controls_frame = ctk.CTkFrame(self.license_history_tab)
        controls_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.user_filter_var = ctk.StringVar(value="Tutti gli Utenti")
        self.user_filter_menu = ctk.CTkOptionMenu(controls_frame, variable=self.user_filter_var, values=["Tutti gli Utenti"], command=self._on_user_filter_selected)
        self.user_filter_menu.pack(side="left", padx=5, pady=5)

        ctk.CTkButton(controls_frame, text="Aggiorna Storico", command=self._refresh_license_history).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(controls_frame, text="Elimina Selezionato", command=self._delete_selected_license, fg_color="red").pack(side="right", padx=5, pady=5)

        self.history_status_label = ctk.CTkLabel(self.license_history_tab, text="", anchor="w")
        self.history_status_label.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.history_list_frame = ctk.CTkScrollableFrame(self.license_history_tab, label_text="Storico Licenze Generate")
        self.history_list_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.history_list_frame.grid_columnconfigure(0, weight=1)
        self._refresh_license_history()

    def open_licenses_folder(self):
        base_license_path = "C:\\Users\\Coemi\\Desktop\\SCRIPT\\crea-licenze-pyarmor\\licenze"
        try:
            os.startfile(base_license_path)
        except FileNotFoundError:
            messagebox.showerror("Errore", f"La cartella non esiste:\n{base_license_path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire la cartella:\n{e}")

    def _refresh_all_user_views(self):
        self._refresh_user_dropdowns()
        self._refresh_user_list()
        self._refresh_license_history()

    def _refresh_user_dropdowns(self):
        self.user_data_map.clear()
        users = self.db.get_all_users()
        user_names = ["Nessun utente selezionato"]
        if users:
            for user_id, name, hwid, dest_path in users:
                self.user_data_map[name] = (user_id, hwid, dest_path)
                user_names.append(name)

        # Update dropdowns in both tabs
        self.user_filter_menu.configure(values=["All Users"] + user_names[1:]) # History tab
        self.license_user_dropdown.configure(values=user_names) # License tab
        self.license_user_dropdown_var.set("Nessun utente selezionato")
        self._clear_license_fields()

    def _on_license_user_selected(self, selected_name):
        if selected_name in self.user_data_map:
            user_id, hwid, dest_path = self.user_data_map[selected_name]
            self.selected_user_id_for_license = user_id
            self.device_id.set(hwid)
        else:
            self._clear_license_fields()

    def _clear_license_fields(self):
        self.selected_user_id_for_license = None
        self.device_id.set("")
        self.expiry_date.set("")

    def _set_two_months_expiry(self):
        from datetime import datetime, timedelta
        # You might need to install this: pip install python-dateutil
        try:
            from dateutil.relativedelta import relativedelta
            future_date = datetime.now() + relativedelta(months=2)
            self.expiry_date.set(future_date.strftime("%Y-%m-%d"))
        except ImportError:
            messagebox.showerror("Error", "Package 'python-dateutil' not found. Cannot set expiry.\nPlease install it: pip install python-dateutil")


    def create_user_management_tab(self):
        self.selected_user_for_edit = tk.StringVar()
        self.user_management_tab.grid_columnconfigure(0, weight=1)
        self.user_management_tab.grid_rowconfigure(0, weight=1)

        button_frame = ctk.CTkFrame(self.user_management_tab)
        button_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkButton(button_frame, text="Aggiungi Utente", command=self._open_add_edit_user_popup).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Modifica Utente Selezionato", command=lambda: self._open_add_edit_user_popup(edit_mode=True)).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Elimina Utente Selezionato", command=self._delete_selected_user, fg_color="red").pack(side="left", padx=5)

        self.user_list_frame = ctk.CTkScrollableFrame(self.user_management_tab, label_text="Utenti Registrati")
        self.user_list_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.user_list_frame.grid_columnconfigure(0, weight=1)

        self.user_status_label = ctk.CTkLabel(self.user_management_tab, text="", anchor="w")
        self.user_status_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self._refresh_user_list()

    def _refresh_user_list(self):
        for widget in self.user_list_frame.winfo_children():
            widget.destroy()

        all_users = self.db.get_all_users()

        # Main container for the list
        list_container = ctk.CTkFrame(self.user_list_frame, fg_color="transparent")
        list_container.pack(fill="x", expand=True)

        # Configure columns for the grid layout in the main container
        list_container.grid_columnconfigure(0, weight=0, minsize=80)  # Select
        list_container.grid_columnconfigure(1, weight=1)             # Name
        list_container.grid_columnconfigure(2, weight=1)             # HWID
        list_container.grid_columnconfigure(3, weight=2)             # Path

        # Header
        header_frame = ctk.CTkFrame(list_container, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 5))
        header_frame.grid_columnconfigure(0, weight=0, minsize=80)
        header_frame.grid_columnconfigure(1, weight=1)
        header_frame.grid_columnconfigure(2, weight=1)
        header_frame.grid_columnconfigure(3, weight=2)

        ctk.CTkLabel(header_frame, text="Seleziona", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, sticky="w")
        ctk.CTkLabel(header_frame, text="Nome Utente", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=5, sticky="w")
        ctk.CTkLabel(header_frame, text="Serial N. Disco rigido", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=5, sticky="w")
        ctk.CTkLabel(header_frame, text="Percorso Destinazione", font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, padx=5, sticky="w")

        if not all_users:
            ctk.CTkLabel(list_container, text="Nessun utente registrato.").grid(row=1, column=0, columnspan=4, pady=10)
            return

        for i, (user_id, name, hwid, dest_path) in enumerate(all_users):
            row_index = i + 1
            radio_button = ctk.CTkRadioButton(list_container, text="", variable=self.selected_user_for_edit, value=str(user_id))
            radio_button.grid(row=row_index, column=0, padx=10, pady=5, sticky="w")

            ctk.CTkLabel(list_container, text=name, anchor="w").grid(row=row_index, column=1, padx=5, pady=5, sticky="ew")
            ctk.CTkLabel(list_container, text=hwid, anchor="w").grid(row=row_index, column=2, padx=5, pady=5, sticky="ew")
            ctk.CTkLabel(list_container, text=dest_path or "Non impostato", anchor="w").grid(row=row_index, column=3, padx=5, pady=5, sticky="ew")

    def _open_add_edit_user_popup(self, edit_mode=False):
        user_id_to_edit = self.selected_user_for_edit.get()
        if edit_mode and not user_id_to_edit:
            self.user_status_label.configure(text="Errore: Nessun utente selezionato per la modifica.", text_color="red")
            return

        popup = ctk.CTkToplevel(self)
        popup.transient(self)
        popup.grab_set()

        if edit_mode:
            popup.title("Modifica Utente")
            user_data = next((u for u in self.db.get_all_users() if str(u[0]) == user_id_to_edit), None)
            if not user_data:
                self.user_status_label.configure(text="Errore: Utente non trovato.", text_color="red")
                popup.destroy()
                return
        else:
            popup.title("Aggiungi Nuovo Utente")
            user_data = None

        ctk.CTkLabel(popup, text="Nome Utente:").pack(pady=(10, 0))
        name_entry = ctk.CTkEntry(popup, width=300)
        name_entry.pack(pady=5, padx=10)
        if user_data: name_entry.insert(0, user_data[1])

        ctk.CTkLabel(popup, text="Serial N. Disco rigido:").pack()
        hwid_entry = ctk.CTkEntry(popup, width=300)
        hwid_entry.pack(pady=5, padx=10)
        if user_data: hwid_entry.insert(0, user_data[2])

        ctk.CTkLabel(popup, text="Percorso Destinazione:").pack()
        dest_path_entry = ctk.CTkEntry(popup, width=300)
        dest_path_entry.pack(pady=5, padx=10)
        if user_data and user_data[3]: dest_path_entry.insert(0, user_data[3])

        def save_action():
            name = name_entry.get().strip()
            hwid = hwid_entry.get().strip()
            dest_path = dest_path_entry.get().strip()
            if not name or not hwid: return

            if edit_mode:
                success, msg = self.db.update_user(user_id_to_edit, name, hwid, dest_path)
            else:
                # Automatic folder creation and path assignment
                base_license_path = "C:\\Users\\Coemi\\Desktop\\SCRIPT\\crea-licenze-pyarmor\\licenze"
                user_folder = os.path.join(base_license_path, name)
                try:
                    os.makedirs(user_folder, exist_ok=True)
                    dest_path = user_folder
                except OSError as e:
                    messagebox.showerror("Errore Creazione Cartella", f"Impossibile creare la cartella per l'utente:\n{e}")
                    return

                success, msg = self.db.add_user(name, hwid, dest_path)

            if success:
                self.user_status_label.configure(text=msg, text_color="green")
                self._refresh_all_user_views()
                popup.destroy()
            else:
                error_label = ctk.CTkLabel(popup, text=msg, text_color="red")
                error_label.pack(pady=5)

        ctk.CTkButton(popup, text="Salva", command=save_action).pack(pady=10)

    def _delete_selected_user(self):
        user_id_to_delete = self.selected_user_for_edit.get()
        if not user_id_to_delete:
            self.user_status_label.configure(text="Errore: Nessun utente selezionato.", text_color="red")
            return

        dialog = ctk.CTkInputDialog(text="Sei sicuro di voler eliminare questo utente?\nScrivi 'DELETE' per confermare.", title="Conferma Eliminazione")
        confirmation = dialog.get_input()

        if confirmation == "DELETE":
            success, msg = self.db.delete_user(user_id_to_delete)
            self.user_status_label.configure(text=msg, text_color="green" if success else "red")
            self._refresh_all_user_views()
            self.selected_user_for_edit.set("")
        else:
            self.user_status_label.configure(text="Eliminazione annullata.", text_color="orange")

    def _on_user_filter_selected(self, selected_name):
        self._refresh_license_history()

    def _refresh_license_history(self):
        for widget in self.history_list_frame.winfo_children():
            widget.destroy()

        selected_user_name = self.user_filter_var.get()
        history_data = []
        if selected_user_name == "Tutti gli Utenti":
            history_data = self.db.get_license_history()
        elif selected_user_name in self.user_data_map:
            user_id, _, _ = self.user_data_map[selected_user_name]
            history_data = self.db.get_license_history_by_user(user_id)

        header = ctk.CTkFrame(self.history_list_frame, fg_color=("gray85", "gray20"))
        header.pack(fill="x", pady=(0, 5), padx=5)
        header.grid_columnconfigure(0, weight=0) # Radio button
        header.grid_columnconfigure(1, weight=2) # User
        header.grid_columnconfigure(2, weight=1) # Expiry
        header.grid_columnconfigure(3, weight=1) # Generated

        ctk.CTkLabel(header, text="", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=2)
        ctk.CTkLabel(header, text="Nome Utente", font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, padx=5, pady=2, sticky="w")
        ctk.CTkLabel(header, text="Data Scadenza", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=5, pady=2, sticky="w")
        ctk.CTkLabel(header, text="Data Generazione", font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, padx=5, pady=2, sticky="w")

        if not history_data:
            ctk.CTkLabel(self.history_list_frame, text="Nessuna licenza trovata nello storico.").pack(pady=10)
            return

        for i, (license_id, user_name, expiry_date, generation_date) in enumerate(history_data):
            row_color = ("#f0f0f0", "#303030") if i % 2 == 0 else ("#e0e0e0", "#252525")
            row_frame = ctk.CTkFrame(self.history_list_frame, fg_color=row_color)
            row_frame.pack(fill="x", pady=1, padx=5)
            row_frame.grid_columnconfigure(1, weight=2)
            row_frame.grid_columnconfigure(2, weight=1)
            row_frame.grid_columnconfigure(3, weight=1)

            radio = ctk.CTkRadioButton(row_frame, text="", variable=self.selected_license_id, value=str(license_id))
            radio.grid(row=0, column=0, padx=5, pady=2)
            ctk.CTkLabel(row_frame, text=user_name, anchor="w").grid(row=0, column=1, padx=5, pady=2, sticky="w")
            ctk.CTkLabel(row_frame, text=expiry_date, anchor="w").grid(row=0, column=2, padx=5, pady=2, sticky="w")
            ctk.CTkLabel(row_frame, text=generation_date, anchor="w").grid(row=0, column=3, padx=5, pady=2, sticky="w")

    def _delete_selected_license(self):
        license_id_to_delete = self.selected_license_id.get()
        if not license_id_to_delete:
            self.history_status_label.configure(text="Error: No license selected to delete.", text_color="red")
            return

        # Confirmation Dialog
        dialog = ctk.CTkInputDialog(text="Are you sure you want to delete this license record?\nType 'DELETE' to confirm.", title="Confirm Deletion")
        confirmation = dialog.get_input()

        if confirmation == "DELETE":
            success, msg = self.db.delete_license_record(license_id_to_delete)
            if success:
                self.history_status_label.configure(text=msg, text_color="green")
                self.selected_license_id.set("") # Clear selection
                self._refresh_license_history()
            else:
                self.history_status_label.configure(text=msg, text_color="red")
        else:
            self.history_status_label.configure(text="Deletion cancelled.", text_color="orange")

    def license_generation_process(self, expiry_date, device_id, output_folder, user_id, user_name, queue_obj):
        try:
            queue_obj.put("--- Starting License Generation ---\n")
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", expiry_date):
                raise ValueError("Invalid date format. Please use YYYY-MM-DD.")
            queue_obj.put(f"Expiry: {expiry_date}, Device ID: {device_id}\n")

            cmd1_list = ["pyarmor", "gen", "key", "-O", output_folder, "-e", expiry_date, "-b", device_id]
            queue_obj.put(f"Executing: {' '.join(shlex.quote(arg) for arg in cmd1_list)}\n")
            proc1 = subprocess.run(cmd1_list, capture_output=True, text=True, encoding='utf-8', errors='ignore', check=False)

            success = False
            p = pathlib.Path(output_folder)
            if list(p.glob("*.lic")) or list(p.glob("*.rkey")):
                success = True

            if not success:
                queue_obj.put(f"STDOUT:\n{proc1.stdout}\nSTDERR:\n{proc1.stderr}\n")
                queue_obj.put("First attempt failed. Retrying with 'disk:' prefix...\n")
                time.sleep(1)
                cmd2_list = ["pyarmor", "gen", "key", "-O", output_folder, "-e", expiry_date, "-b", f"disk:{device_id}"]
                queue_obj.put(f"Executing: {' '.join(shlex.quote(arg) for arg in cmd2_list)}\n")
                proc2 = subprocess.run(cmd2_list, capture_output=True, text=True, encoding='utf-8', errors='ignore', check=False)
                if list(p.glob("*.lic")) or list(p.glob("*.rkey")):
                    success = True
                final_proc = proc2
            else:
                final_proc = proc1

            queue_obj.put(f"Final STDOUT:\n{final_proc.stdout}\n")
            queue_obj.put(f"Final STDERR:\n{final_proc.stderr}\n")

            if success:
                # Create infoLicense.txt
                info_path = os.path.join(output_folder, "infoLicense.txt")
                creation_date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                expiry_date_formatted = datetime.datetime.strptime(expiry_date, "%Y-%m-%d").strftime("%d/%m/%Y")

                info_content = f"""
============================================
\t\tINFORMAZIONI LICENZA
============================================
Utenza:\t\t\tHardware ID Associato:
{user_name}\t\t{device_id}

Data di Scadenza:\t\tData creazione:
{expiry_date_formatted}\t\t{creation_date}
============================================
"""
                with open(info_path, 'w', encoding='utf-8') as f:
                    f.write(info_content.strip())
                queue_obj.put(f"Created infoLicense.txt at: {info_path}\n")

                # Pass data back to the main thread to be added to the database
                queue_obj.put(("ADD_LICENSE_RECORD", user_id, expiry_date))
                queue_obj.put("\n--- SUCCESS! ---\nLicense key created. Recording to history...\n")
            else:
                error_details = final_proc.stderr if final_proc.stderr else final_proc.stdout
                raise RuntimeError(f"License generation failed. Details: {error_details.strip()}")

        except Exception as e:
            queue_obj.put(f"\n--- AN ERROR OCCURRED ---\n{traceback.format_exc()}\n{str(e)}\n")
        finally:
            queue_obj.put(("LICENSE_PROCESS_COMPLETE",))


    def _run_obfuscation_process(self):
        try:
            build_dir = "build"
            dest_dir = self.destination_path.get()
            license_src_path = self.license_path.get()
            main_script = "gui.py"
            source_dir = self.source_path.get()

            self.obfuscation_queue.put("Starting build process...\n")

            # 1. Clean up and Create build directory
            if os.path.exists(build_dir):
                shutil.rmtree(build_dir)
            os.makedirs(build_dir)

            # 2. Copy ALL files to build directory, excluding specified files
            self.obfuscation_queue.put("Copying application files to temporary build directory...\n")

            # List of files to exclude from the final package
            excluded_files = [
                'obfuscator_gui.py',
                'license_manager.py',
                'gestionale_licenze.db',
                'database.py',
                'avvio_gestionale.bat'
            ]

            files_to_copy = glob.glob(os.path.join(source_dir, '*.*')) # Get all files initially

            for f in files_to_copy:
                filename = os.path.basename(f)
                if filename not in excluded_files:
                    try:
                        shutil.copy(f, build_dir)
                    except Exception as e:
                        self.obfuscation_queue.put(f"Could not copy {filename}: {e}\n")
                else:
                    self.obfuscation_queue.put(f"Excluding: {filename}\n")

            setup_dir_src = os.path.join(source_dir, 'file di setup')
            if os.path.exists(setup_dir_src):
                shutil.copytree(setup_dir_src, os.path.join(build_dir, 'file di setup'))
            self.obfuscation_queue.put("All source files copied.\n")

            # 3. Explicitly find and list ALL Python scripts to be obfuscated.
            self.obfuscation_queue.put("Explicitly listing all Python scripts for obfuscation...\n")
            all_scripts = [os.path.basename(f) for f in glob.glob(os.path.join(build_dir, '*.py'))]

            if main_script in all_scripts:
                all_scripts.insert(0, all_scripts.pop(all_scripts.index(main_script)))

            if not all_scripts:
                raise FileNotFoundError("No Python files found in build directory.")

            self.obfuscation_queue.put(f"Scripts to be processed: {', '.join(all_scripts)}\n")

            # 4. Obfuscate by passing the explicit list of all scripts.
            self.obfuscation_queue.put("\n--- Running PyArmor ---\n")
            command = [
                "pyarmor", "gen",
                "--outer",
                "--output", os.path.abspath(dest_dir),
            ]
            command.extend(all_scripts)

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                encoding='utf-8',
                errors='ignore',
                cwd=build_dir
            )

            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.obfuscation_queue.put(output.strip() + '\n')
            rc = process.poll()
            self.obfuscation_queue.put("--- PyArmor Finished ---\n\n")

            if rc == 0:
                self.obfuscation_queue.put("Obfuscation successful!\n")

                # 5. Create a portable Python runtime for maximum compatibility
                self.obfuscation_queue.put("Creating portable Python runtime...\n")
                python_dir = os.path.dirname(sys.executable)

                runtime_files = [
                    'python.exe', 'pythonw.exe', 'python3.dll',
                    f'python{sys.version_info.major}{sys.version_info.minor}.dll',
                    'vcruntime140.dll', 'vcruntime140_1.dll'
                ]

                for filename in runtime_files:
                    src_path = os.path.join(python_dir, filename)
                    if os.path.exists(src_path):
                        self.obfuscation_queue.put(f" - Copying {filename}...\n")
                        shutil.copy(src_path, dest_dir)

                # Copy essential subfolders for Python and Tkinter
                for folder in ['DLLs', 'Lib', 'tcl']:
                    src_path = os.path.join(python_dir, folder)
                    dest_path = os.path.join(dest_dir, folder)
                    if os.path.exists(src_path):
                        self.obfuscation_queue.put(f" - Copying '{folder}' subfolder...\n")
                        if os.path.exists(dest_path):
                            shutil.rmtree(dest_path)
                        shutil.copytree(src_path, dest_path)

                self.obfuscation_queue.put("Portable runtime created.\n")

                # 6. Copy non-Python assets
                self.obfuscation_queue.put("Copying non-Python assets to final destination...\n")
                for asset_file in glob.glob(os.path.join(build_dir, '*.*')):
                    if not asset_file.endswith('.py'):
                        shutil.copy(asset_file, dest_dir)

                setup_dir_build = os.path.join(build_dir, 'file di setup')
                setup_dir_dest = os.path.join(dest_dir, 'file di setup')
                if os.path.exists(setup_dir_build):
                    if os.path.exists(setup_dir_dest):
                        shutil.rmtree(setup_dir_dest)
                    shutil.copytree(setup_dir_build, setup_dir_dest)
                self.obfuscation_queue.put("Assets copied.\n")

                # 7. Copy license file
                if license_src_path:
                    self.obfuscation_queue.put(f"Copying license file to {dest_dir}...\n")
                    shutil.copy(license_src_path, dest_dir)
                    self.obfuscation_queue.put("License file copied.\n")

                # 8. Create avvio.bat launcher
                self.obfuscation_queue.put("Creating launcher script (avvio.bat)...\n")
                launcher_path = os.path.join(dest_dir, 'avvio.bat')
                launcher_content = f'''@echo off
setlocal
REM Change directory to the script's location
cd /d %~dp0
REM Run the application using the LOCAL python.exe
.\\python.exe "{main_script}"
endlocal
pause
'''
                with open(launcher_path, 'w', encoding='utf-8') as f:
                    f.write(launcher_content)
                self.obfuscation_queue.put("Launcher script created.\n")
                self.obfuscation_queue.put(f"\nSUCCESS: Final application is ready in: {dest_dir}\n")
            else:
                self.obfuscation_queue.put(f"Error: PyArmor process returned error code {rc}.\n")

        except Exception as e:
            self.obfuscation_queue.put(f"\nAn unexpected error occurred: {str(e)}\n")
        finally:
            self.obfuscation_queue.put(("PROCESS_COMPLETE",))

if __name__ == "__main__":
    db_conn = None
    try:
        # Assicurati che 'database.py' sia nella stessa cartella
        db_conn = Database() 
        app = ObfuscatorApp(db_conn)
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
    except NameError:
         print("ERRORE: Impossibile trovare la classe 'Database'. Assicurati che il file 'database.py' esista.")
    except Exception as e:
        print(f"Error during application startup: {e}")
        traceback.print_exc()
    finally:
        if db_conn:
            db_conn.close()
            print("Database connection closed.")