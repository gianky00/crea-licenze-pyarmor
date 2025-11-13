import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import subprocess
import shutil
import os
import glob
import queue
import sys

class ObfuscatorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Application Obfuscator")
        self.geometry("600x450")
        self.source_path = tk.StringVar()
        self.destination_path = tk.StringVar()
        self.license_path = tk.StringVar()
        self.queue = queue.Queue()

        # Frame for source path selection
        source_path_frame = tk.Frame(self, pady=5)
        source_path_frame.pack(fill='x', padx=10, pady=(10,0))
        tk.Label(source_path_frame, text="Source Folder:").pack(side='left')
        self.source_path_entry = tk.Entry(source_path_frame, textvariable=self.source_path, state='readonly', width=50)
        self.source_path_entry.pack(side='left', expand=True, fill='x', padx=5)
        self.browse_source_button = tk.Button(source_path_frame, text="Browse...", command=self.select_source)
        self.browse_source_button.pack(side='left')

        # Frame for destination path selection
        dest_path_frame = tk.Frame(self, pady=5)
        dest_path_frame.pack(fill='x', padx=10, pady=(10,0))
        tk.Label(dest_path_frame, text="Destination Folder:").pack(side='left')
        self.dest_path_entry = tk.Entry(dest_path_frame, textvariable=self.destination_path, state='readonly', width=50)
        self.dest_path_entry.pack(side='left', expand=True, fill='x', padx=5)
        self.browse_dest_button = tk.Button(dest_path_frame, text="Browse...", command=self.select_destination)
        self.browse_dest_button.pack(side='left')

        # Frame for license file selection
        license_path_frame = tk.Frame(self, pady=5)
        license_path_frame.pack(fill='x', padx=10)
        tk.Label(license_path_frame, text="License File (.lic):").pack(side='left')
        self.license_path_entry = tk.Entry(license_path_frame, textvariable=self.license_path, state='readonly', width=50)
        self.license_path_entry.pack(side='left', expand=True, fill='x', padx=5)
        self.browse_license_button = tk.Button(license_path_frame, text="Browse...", command=self.select_license_file)
        self.browse_license_button.pack(side='left')

        # Start Button
        self.start_button = tk.Button(self, text="Start Obfuscation", command=self.start_obfuscation, state='disabled', font=('Helvetica', 12, 'bold'), pady=10)
        self.start_button.pack(pady=10)

        # Status Area
        status_frame = tk.Frame(self, pady=10)
        status_frame.pack(expand=True, fill='both', padx=10)
        tk.Label(status_frame, text="Status:").pack(anchor='w')
        self.status_text = tk.Text(status_frame, height=10, state='disabled', bg='black', fg='white', font=('Courier', 9))
        self.status_text.pack(expand=True, fill='both')

    def _update_status(self, message):
        self.status_text.config(state='normal')
        self.status_text.insert(tk.END, message)
        self.status_text.see(tk.END)
        self.status_text.config(state='disabled')

    def select_source(self):
        path = filedialog.askdirectory(title="Select Source Folder")
        if path:
            self.source_path.set(path)
            if self.destination_path.get():
                self.start_button.config(state='normal')
            self._update_status(f"Source set to: {path}\n")

    def select_destination(self):
        path = filedialog.askdirectory(title="Select Destination Folder")
        if path:
            self.destination_path.set(path)
            if self.source_path.get():
                self.start_button.config(state='normal')
            self._update_status(f"Destination set to: {path}\n")

    def select_license_file(self):
        path = filedialog.askopenfilename(
            title="Select License File",
            filetypes=[("License Files", "*.lic *.rkey"), ("All files", "*.*")]
        )
        if path:
            self.license_path.set(path)
            self._update_status(f"License file set to: {path}\n")

    def start_obfuscation(self):
        if not self.source_path.get() or not self.destination_path.get():
            messagebox.showerror("Error", "Please select both a source and destination folder.")
            return

        self.start_button.config(state='disabled')
        self.browse_source_button.config(state='disabled')
        self.browse_dest_button.config(state='disabled')
        self.browse_license_button.config(state='disabled')
        self.status_text.config(state='normal')
        self.status_text.delete('1.0', tk.END)
        self.status_text.config(state='disabled')

        self._process_queue()
        thread = threading.Thread(target=self._run_obfuscation_process)
        thread.daemon = True
        thread.start()

    def _process_queue(self):
        try:
            while not self.queue.empty():
                message = self.queue.get_nowait()
                if isinstance(message, tuple) and message[0] == "PROCESS_COMPLETE":
                    self.start_button.config(state='normal')
                    self.browse_source_button.config(state='normal')
                    self.browse_dest_button.config(state='normal')
                    self.browse_license_button.config(state='normal')
                    build_dir = "build"
                    if os.path.exists(build_dir):
                        shutil.rmtree(build_dir)
                    self._update_status("\nCleanup complete. Ready for next operation.\n")
                else:
                    self._update_status(message)
        finally:
            self.after(100, self._process_queue)

    def _run_obfuscation_process(self):
        try:
            build_dir = "build"
            dest_dir = self.destination_path.get()
            license_src_path = self.license_path.get()
            main_script = "gui.py"
            source_dir = self.source_path.get()

            self.queue.put("Starting build process...\n")

            # 1. Clean up and Create build directory
            if os.path.exists(build_dir):
                shutil.rmtree(build_dir)
            os.makedirs(build_dir)

            # 2. Copy ALL files to build directory, excluding specified files
            self.queue.put("Copying application files to temporary build directory...\n")

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
                        self.queue.put(f"Could not copy {filename}: {e}\n")
                else:
                    self.queue.put(f"Excluding: {filename}\n")

            setup_dir_src = os.path.join(source_dir, 'file di setup')
            if os.path.exists(setup_dir_src):
                shutil.copytree(setup_dir_src, os.path.join(build_dir, 'file di setup'))
            self.queue.put("All source files copied.\n")

            # 3. Explicitly find and list ALL Python scripts to be obfuscated.
            self.queue.put("Explicitly listing all Python scripts for obfuscation...\n")
            all_scripts = [os.path.basename(f) for f in glob.glob(os.path.join(build_dir, '*.py'))]
            
            if main_script in all_scripts:
                all_scripts.insert(0, all_scripts.pop(all_scripts.index(main_script)))
            
            if not all_scripts:
                raise FileNotFoundError("No Python files found in build directory.")
                
            self.queue.put(f"Scripts to be processed: {', '.join(all_scripts)}\n")

            # 4. Obfuscate by passing the explicit list of all scripts.
            self.queue.put("\n--- Running PyArmor ---\n")
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
                    self.queue.put(output.strip() + '\n')
            rc = process.poll()
            self.queue.put("--- PyArmor Finished ---\n\n")

            if rc == 0:
                self.queue.put("Obfuscation successful!\n")
                
                # 5. Create a portable Python runtime for maximum compatibility
                self.queue.put("Creating portable Python runtime...\n")
                python_dir = os.path.dirname(sys.executable)
                
                runtime_files = [
                    'python.exe', 'pythonw.exe', 'python3.dll',
                    f'python{sys.version_info.major}{sys.version_info.minor}.dll',
                    'vcruntime140.dll', 'vcruntime140_1.dll'
                ]
                
                for filename in runtime_files:
                    src_path = os.path.join(python_dir, filename)
                    if os.path.exists(src_path):
                        self.queue.put(f"  - Copying {filename}...\n")
                        shutil.copy(src_path, dest_dir)

                # Copy essential subfolders for Python and Tkinter
                for folder in ['DLLs', 'Lib', 'tcl']:
                    src_path = os.path.join(python_dir, folder)
                    dest_path = os.path.join(dest_dir, folder)
                    if os.path.exists(src_path):
                        self.queue.put(f"  - Copying '{folder}' subfolder...\n")
                        if os.path.exists(dest_path):
                            shutil.rmtree(dest_path)
                        shutil.copytree(src_path, dest_path)
                
                self.queue.put("Portable runtime created.\n")

                # 6. Copy non-Python assets
                self.queue.put("Copying non-Python assets to final destination...\n")
                for asset_file in glob.glob(os.path.join(build_dir, '*.*')):
                    if not asset_file.endswith('.py'):
                        shutil.copy(asset_file, dest_dir)
                
                setup_dir_build = os.path.join(build_dir, 'file di setup')
                setup_dir_dest = os.path.join(dest_dir, 'file di setup')
                if os.path.exists(setup_dir_build):
                    if os.path.exists(setup_dir_dest):
                        shutil.rmtree(setup_dir_dest)
                    shutil.copytree(setup_dir_build, setup_dir_dest)
                self.queue.put("Assets copied.\n")

                # 7. Copy license file
                if license_src_path:
                    self.queue.put(f"Copying license file to {dest_dir}...\n")
                    shutil.copy(license_src_path, dest_dir)
                    self.queue.put("License file copied.\n")

                # 8. Create avvio.bat launcher
                self.queue.put("Creating launcher script (avvio.bat)...\n")
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
                self.queue.put("Launcher script created.\n")
                self.queue.put(f"\nSUCCESS: Final application is ready in: {dest_dir}\n")
            else:
                self.queue.put(f"Error: PyArmor process returned error code {rc}.\n")

        except Exception as e:
            self.queue.put(f"\nAn unexpected error occurred: {str(e)}\n")
        finally:
            self.queue.put(("PROCESS_COMPLETE",))

if __name__ == "__main__":
    app = ObfuscatorGUI()
    app.mainloop()

