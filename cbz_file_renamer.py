import sys
import traceback
import ctypes

# --- CRASH CATCHER START ---
try:
    import os
    import re
    import threading
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    from config import (
        BG_DARK, BG_PANEL, BG_SURFACE, FG_TEXT, FG_DIM, FG_MUTED,
        ACCENT_BLUE, ACCENT_HOVER, ACCENT_PURPLE, SUCCESS_GREEN,
        TABLE_BG, TABLE_FG, CONFLICT_YELLOW, ERROR_RED, BORDER_COLOR, EDIT_BG,
        load_config, save_config
    )
    from filename_parser import parse_filename, normalize
    from api_sources import fetch_google_books_name, fetch_comicvine_name

    class DarkRenamerApp:
        def __init__(self, root):
            self.root = root
            self.root.title("CBZ Renamer // PRO")
            self.root.geometry("1100x680")
            self.root.minsize(900, 500)
            self.root.configure(bg=BG_DARK)

            self.is_running = True
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

            self._edit_entry = None
            self._edit_item = None

            # ─── Load persisted settings ─────────────────────────────
            cfg = load_config()
            self.setting_scan_mode = tk.StringVar(value=cfg["scan_mode"])
            self.setting_num_padding = tk.IntVar(value=cfg["num_padding"])
            self.setting_include_subtitle = tk.BooleanVar(value=cfg["include_subtitle"])
            self.setting_sub_separator = tk.StringVar(value=cfg["sub_separator"])
            self.setting_online_source = tk.StringVar(value=cfg["online_source"])
            self.comicvine_api_key = tk.StringVar(value=cfg["comicvine_api_key"])
            self.setting_use_source_format = tk.BooleanVar(value=cfg["use_source_format"])

            # --- STYLES ---
            style = ttk.Style()
            try:
                if 'clam' in style.theme_names():
                    style.theme_use('clam')
                else:
                    style.theme_use('alt')
            except Exception:
                pass

            style.configure("Treeview",
                background=TABLE_BG, foreground=TABLE_FG, fieldbackground=TABLE_BG,
                rowheight=28, borderwidth=0, font=('Segoe UI', 9))
            style.configure("Treeview.Heading",
                background=BG_PANEL, foreground=FG_DIM,
                font=('Segoe UI', 8, 'bold'), relief="flat", borderwidth=0)
            style.map("Treeview",
                background=[('selected', '#1a3a5c')],
                foreground=[('selected', '#ffffff')])
            style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

            style.configure("Dark.Vertical.TScrollbar",
                background=BG_PANEL, troughcolor=BG_DARK,
                borderwidth=0, arrowsize=0, relief="flat")
            style.map("Dark.Vertical.TScrollbar",
                background=[('active', '#3a3a3a'), ('!active', '#252525')])

            # --- HEADER ---
            header = tk.Frame(root, bg=BG_PANEL, padx=24, pady=16)
            header.pack(fill=tk.X)

            title_frame = tk.Frame(header, bg=BG_PANEL)
            title_frame.pack(side=tk.LEFT)
            tk.Label(title_frame, text="CBZ RENAMER", bg=BG_PANEL, fg=FG_TEXT,
                     font=("Segoe UI", 15, "bold")).pack(side=tk.LEFT)
            tk.Label(title_frame, text="  //  PRO", bg=BG_PANEL, fg=ACCENT_BLUE,
                     font=("Segoe UI", 15, "bold")).pack(side=tk.LEFT)

            self.btn_gear = tk.Button(header, text="\u2699", command=self.open_settings,
                bg=BG_PANEL, fg=FG_DIM, activebackground=BG_PANEL, activeforeground=FG_TEXT,
                font=("Segoe UI", 16), relief="flat", borderwidth=0, cursor="hand2",
                highlightthickness=0, padx=8)
            self.btn_gear.pack(side=tk.LEFT, padx=(16, 0))

            self.lbl_path = tk.Label(header, text="No folder selected", bg=BG_PANEL, fg=FG_DIM,
                                     font=("Consolas", 9), padx=12, pady=4)
            self.lbl_path.pack(side=tk.RIGHT)

            tk.Frame(root, bg=ACCENT_BLUE, height=1).pack(fill=tk.X)

            # --- CONTROLS ---
            controls = tk.Frame(root, bg=BG_DARK, padx=24, pady=14)
            controls.pack(fill=tk.X)

            self.btn_browse = self._make_btn(controls, "  OPEN FOLDER  ", self.select_folder, "#2a2a2a", FG_TEXT)
            self.btn_browse.pack(side=tk.LEFT, padx=(0, 8))

            self.btn_scan = self._make_btn(controls, "  SCAN  ", self.start_scan_thread, "#333", FG_DIM)
            self.btn_scan.pack(side=tk.LEFT, padx=8)
            self.btn_scan.config(state=tk.DISABLED)

            self.btn_apply = self._make_btn(controls, "  APPLY RENAME  ", self.apply_rename, "#333", FG_DIM)
            self.btn_apply.pack(side=tk.RIGHT)
            self.btn_apply.config(state=tk.DISABLED)

            self.hint_lbl = tk.Label(controls, text="Double-click Final to edit  \u00b7  Right-click to toggle Web/Local",
                                     bg=BG_DARK, fg="#444444", font=("Segoe UI", 8))
            self.hint_lbl.pack(side=tk.RIGHT, padx=(0, 16))

            # --- TABLE ---
            table_outer = tk.Frame(root, bg=BORDER_COLOR, padx=1, pady=1)
            table_outer.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 8))

            table_frame = tk.Frame(table_outer, bg=TABLE_BG)
            table_frame.pack(fill=tk.BOTH, expand=True)

            cols = ("original", "online", "backup", "final", "status")
            self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")

            self.tree.heading("original", text="ORIGINAL FILE", anchor="w")
            self.tree.heading("online",   text="WEB MATCH",     anchor="w")
            self.tree.heading("backup",   text="LOCAL GUESS",   anchor="w")
            self.tree.heading("final",    text="FINAL NAME",    anchor="w")
            self.tree.heading("status",   text="STATUS",        anchor="center")

            self.tree.column("original", width=240, minwidth=120)
            self.tree.column("online",   width=180, minwidth=100)
            self.tree.column("backup",   width=180, minwidth=100)
            self.tree.column("final",    width=260, minwidth=140)
            self.tree.column("status",   width=100, minwidth=70, anchor="center")

            scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview,
                                    style="Dark.Vertical.TScrollbar")
            self.tree.configure(yscroll=scroll.set)
            scroll.pack(side=tk.RIGHT, fill=tk.Y)
            self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            self.tree.bind("<Double-1>", self.on_double_click)
            self.tree.bind("<Button-3>", self.on_right_click)

            self.tree.tag_configure("conflict",  foreground=CONFLICT_YELLOW)
            self.tree.tag_configure("match",     foreground=SUCCESS_GREEN)
            self.tree.tag_configure("offline",   foreground=FG_DIM)
            self.tree.tag_configure("duplicate", foreground=ERROR_RED)
            self.tree.tag_configure("edited",    foreground=ACCENT_BLUE)
            self.tree.tag_configure("ready",     foreground=TABLE_FG)

            # --- STATUS BAR ---
            status_bar = tk.Frame(root, bg=BG_PANEL, height=28)
            status_bar.pack(side=tk.BOTTOM, fill=tk.X)
            self.status_lbl = tk.Label(status_bar, text="Ready", bg=BG_PANEL, fg=FG_DIM,
                                       font=("Segoe UI", 8))
            self.status_lbl.pack(side=tk.LEFT, padx=24, pady=4)
            self.file_count_lbl = tk.Label(status_bar, text="", bg=BG_PANEL, fg=FG_DIM,
                                            font=("Segoe UI", 8))
            self.file_count_lbl.pack(side=tk.RIGHT, padx=24, pady=4)

            # Logic
            self.selected_directory = None
            self.rename_data = {}
            self.series_cache = {}
            self.scan_in_progress = False

        # ─── UI Helpers ──────────────────────────────────────────────

        def _make_btn(self, parent, text, cmd, bg_color, fg_color):
            return tk.Button(parent, text=text, command=cmd,
                bg=bg_color, fg=fg_color, activebackground=ACCENT_HOVER, activeforeground="white",
                font=("Segoe UI", 9, "bold"), relief="flat", pady=7, padx=14,
                borderwidth=0, cursor="hand2", highlightthickness=0)

        def _enable_btn(self, btn, bg_color):
            btn.config(state=tk.NORMAL, bg=bg_color, fg="white")

        def _disable_btn(self, btn):
            btn.config(state=tk.DISABLED, bg="#333", fg=FG_DIM)

        def on_closing(self):
            self._save_settings()
            self.is_running = False
            self._destroy_edit()
            self.root.destroy()

        def _save_settings(self):
            save_config({
                "scan_mode": self.setting_scan_mode.get(),
                "num_padding": self.setting_num_padding.get(),
                "include_subtitle": self.setting_include_subtitle.get(),
                "sub_separator": self.setting_sub_separator.get(),
                "online_source": self.setting_online_source.get(),
                "comicvine_api_key": self.comicvine_api_key.get(),
                "use_source_format": self.setting_use_source_format.get()
            })

        # ─── Settings Dialog ─────────────────────────────────────────

        def open_settings(self):
            dlg = tk.Toplevel(self.root)
            dlg.title("Settings")
            dlg.configure(bg=BG_DARK)
            dlg.geometry("460x620")
            dlg.resizable(False, False)
            dlg.transient(self.root)
            dlg.grab_set()

            dlg.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 230
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 310
            dlg.geometry(f"+{x}+{y}")

            # Header
            hdr = tk.Frame(dlg, bg=BG_PANEL, padx=24, pady=14)
            hdr.pack(fill=tk.X)
            tk.Label(hdr, text="\u2699  Settings", bg=BG_PANEL, fg=FG_TEXT,
                     font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT)
            tk.Frame(dlg, bg=BORDER_COLOR, height=1).pack(fill=tk.X)

            # Scrollable body
            canvas = tk.Canvas(dlg, bg=BG_DARK, highlightthickness=0, borderwidth=0)
            canvas.pack(fill=tk.BOTH, expand=True)

            body = tk.Frame(canvas, bg=BG_DARK, padx=28, pady=20)
            canvas.create_window((0, 0), window=body, anchor="nw")

            def _on_body_configure(event):
                canvas.configure(scrollregion=canvas.bbox("all"))
                canvas.itemconfig(canvas.find_all()[0], width=event.width)
            body.bind("<Configure>", _on_body_configure)
            canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas.find_all()[0], width=e.width))

            # ── SCAN SOURCE ──
            self._settings_section(body, "SCAN SOURCE")
            mode_frame = tk.Frame(body, bg=BG_DARK)
            mode_frame.pack(fill=tk.X, pady=(4, 16))
            for val, label in [("both", "Local + Online"), ("local", "Local Only"), ("online", "Online Only")]:
                self._dark_radio(mode_frame, label, self.setting_scan_mode, val)

            # ── ONLINE SOURCE ──
            self._settings_section(body, "ONLINE SOURCE")
            src_frame = tk.Frame(body, bg=BG_DARK)
            src_frame.pack(fill=tk.X, pady=(4, 4))
            for val, label in [("google_books", "Google Books  (no key needed)"), ("comicvine", "ComicVine  (requires API key)")]:
                self._dark_radio(src_frame, label, self.setting_online_source, val)

            # API key section
            key_frame = tk.Frame(body, bg=BG_DARK, padx=22)
            key_frame.pack(fill=tk.X, pady=(4, 16))

            tk.Label(key_frame, text="ComicVine API Key:", bg=BG_DARK, fg=FG_DIM,
                     font=("Segoe UI", 8)).pack(anchor="w")

            entry_row = tk.Frame(key_frame, bg=BG_DARK)
            entry_row.pack(fill=tk.X, pady=(4, 2))

            self._key_visible = False
            self._key_entry = tk.Entry(entry_row, textvariable=self.comicvine_api_key, show="\u2022",
                font=("Consolas", 9), bg=BG_SURFACE, fg=FG_TEXT, insertbackground=FG_TEXT,
                selectbackground=ACCENT_BLUE, relief="flat", borderwidth=0, highlightthickness=1,
                highlightcolor=ACCENT_BLUE, highlightbackground=BORDER_COLOR)
            self._key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 6))

            self._btn_show_key = tk.Button(entry_row, text="Show", command=self._toggle_key_visibility,
                bg="#2a2a2a", fg=FG_DIM, activebackground="#3a3a3a", activeforeground=FG_TEXT,
                font=("Segoe UI", 8), relief="flat", borderwidth=0, cursor="hand2",
                highlightthickness=0, padx=8, pady=2)
            self._btn_show_key.pack(side=tk.RIGHT)

            tk.Label(key_frame, text="Get a free key at comicvine.gamespot.com/api",
                     bg=BG_DARK, fg="#444444", font=("Segoe UI", 7)).pack(anchor="w", pady=(2, 0))

            # ── NUMBER PADDING ──
            self._settings_section(body, "NUMBER PADDING")
            pad_frame = tk.Frame(body, bg=BG_DARK)
            pad_frame.pack(fill=tk.X, pady=(4, 16))
            for val, label in [(2, "2 digits  (01, 02, 10)"), (3, "3 digits  (001, 002, 010)")]:
                self._dark_radio(pad_frame, label, self.setting_num_padding, val)

            # ── WEB MATCH ──
            self._settings_section(body, "WEB MATCH")

            # Source format toggle
            sf_cb = tk.Checkbutton(body, text="Use exact formatting from source",
                variable=self.setting_use_source_format,
                bg=BG_DARK, fg=TABLE_FG, selectcolor=BG_SURFACE, activebackground=BG_DARK,
                activeforeground=FG_TEXT, font=("Segoe UI", 9), highlightthickness=0, borderwidth=0)
            sf_cb.pack(anchor="w", pady=(4, 2))

            # Dynamic example label for source format
            self._sf_example = tk.Label(body, text="", bg=BG_DARK, fg=FG_DIM, font=("Consolas", 8))
            self._sf_example.pack(anchor="w", padx=(22, 0), pady=(0, 8))

            def _update_sf_example(*_args):
                if self.setting_use_source_format.get():
                    self._sf_example.config(text="e.g. Berserk Volume 01.cbz  (as returned by API)")
                else:
                    self._sf_example.config(text="e.g. Berserk, Vol. 01.cbz  (standardized)")
            self.setting_use_source_format.trace_add("write", _update_sf_example)
            _update_sf_example()

            # Subtitle options
            cb = tk.Checkbutton(body, text="Include subtitle from API", variable=self.setting_include_subtitle,
                bg=BG_DARK, fg=TABLE_FG, selectcolor=BG_SURFACE, activebackground=BG_DARK,
                activeforeground=FG_TEXT, font=("Segoe UI", 9), highlightthickness=0, borderwidth=0)
            cb.pack(anchor="w", pady=(4, 8))

            sep_frame = tk.Frame(body, bg=BG_DARK, padx=22)
            sep_frame.pack(fill=tk.X, pady=(0, 4))

            tk.Label(sep_frame, text="Separator:", bg=BG_DARK, fg=FG_DIM,
                     font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 8))
            for val, label in [("hyphen", " -  Hyphen"), ("colon", " :  Colon"), ("source", " Match source")]:
                rb = tk.Radiobutton(sep_frame, text=label, variable=self.setting_sub_separator, value=val,
                    bg=BG_DARK, fg=TABLE_FG, selectcolor=BG_SURFACE, activebackground=BG_DARK,
                    activeforeground=FG_TEXT, font=("Segoe UI", 8), highlightthickness=0,
                    borderwidth=0, indicatoron=True)
                rb.pack(side=tk.LEFT, padx=(0, 6))

            tk.Label(body, text="e.g. Berserk, Vol. 03 - Dark Swordsman.cbz",
                     bg=BG_DARK, fg=FG_DIM, font=("Consolas", 8)).pack(anchor="w", padx=(22, 0), pady=(2, 0))

            # ── DONE ──
            btn_frame = tk.Frame(dlg, bg=BG_DARK, pady=14)
            btn_frame.pack(fill=tk.X)
            tk.Button(btn_frame, text="  DONE  ", command=lambda: self._close_settings(dlg),
                bg=ACCENT_BLUE, fg="white", activebackground=ACCENT_HOVER, activeforeground="white",
                font=("Segoe UI", 9, "bold"), relief="flat", padx=24, pady=7,
                borderwidth=0, cursor="hand2", highlightthickness=0).pack()

        def _dark_radio(self, parent, label, var, val):
            rb = tk.Radiobutton(parent, text=label, variable=var, value=val,
                bg=BG_DARK, fg=TABLE_FG, selectcolor=BG_SURFACE, activebackground=BG_DARK,
                activeforeground=FG_TEXT, font=("Segoe UI", 9), highlightthickness=0,
                borderwidth=0, indicatoron=True)
            rb.pack(anchor="w", pady=1)

        def _toggle_key_visibility(self):
            self._key_visible = not self._key_visible
            if self._key_visible:
                self._key_entry.config(show="")
                self._btn_show_key.config(text="Hide")
            else:
                self._key_entry.config(show="\u2022")
                self._btn_show_key.config(text="Show")

        def _settings_section(self, parent, label):
            tk.Label(parent, text=label, bg=BG_DARK, fg=FG_DIM,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w")

        def _close_settings(self, dlg):
            self.series_cache.clear()
            self._save_settings()
            dlg.destroy()

        # ─── Folder / Scan ───────────────────────────────────────────

        def select_folder(self):
            folder = filedialog.askdirectory()
            if folder:
                self.selected_directory = folder
                display = folder if len(folder) < 60 else "..." + folder[-57:]
                self.lbl_path.config(text=display, fg=FG_MUTED)
                self._enable_btn(self.btn_scan, ACCENT_PURPLE)
                self.status_lbl.config(text="Folder loaded \u2014 ready to scan", fg=FG_DIM)
                self.tree.delete(*self.tree.get_children())
                self.rename_data.clear()
                self.file_count_lbl.config(text="")

        def start_scan_thread(self):
            if self.scan_in_progress:
                return
            self.scan_in_progress = True
            self._disable_btn(self.btn_scan)
            self._disable_btn(self.btn_apply)
            self.status_lbl.config(text="Scanning\u2026", fg=ACCENT_BLUE)
            threading.Thread(target=self.run_scan, daemon=True).start()

        def _pad_volume_in_title(self, raw_title, vol_num_padded):
            """Replace the volume number in a raw API title with the zero-padded version.

            e.g. "Berserk Volume 1" + "01" -> "Berserk Volume 01"
                 "Berserk, Vol. 3"  + "03" -> "Berserk, Vol. 03"
                 "Berserk #1"       + "01" -> "Berserk #01"
            """
            def _replace_num(m):
                return m.group(1) + vol_num_padded
            # Try Vol/Volume patterns
            result = re.sub(
                r'((?:Vol\.?|Volume|v\.)\s*)\d+',
                _replace_num, raw_title, count=1, flags=re.IGNORECASE
            )
            if result != raw_title:
                return result
            # Try Chapter patterns
            result = re.sub(
                r'((?:Chapter|Ch\.?)\s*)\d+',
                _replace_num, raw_title, count=1, flags=re.IGNORECASE
            )
            if result != raw_title:
                return result
            # Try # pattern (ComicVine style)
            result = re.sub(
                r'(#)\d+',
                _replace_num, raw_title, count=1
            )
            return result

        def _strip_subtitle_from_title(self, raw_title):
            """Remove the subtitle portion from a raw title.

            e.g. "Berserk, Vol. 1: The Black Swordsman" -> "Berserk, Vol. 1"
                 "Berserk #1 - The Black Swordsman"      -> "Berserk #1"
            """
            # Try Vol/Volume pattern
            cleaned = re.split(
                r'((?:Vol\.?|Volume|v\.)\s*\d+)\s*[:\-\u2013\u2014]\s*.+',
                raw_title, maxsplit=1, flags=re.IGNORECASE
            )
            if len(cleaned) > 1:
                return cleaned[0] + cleaned[1]
            # Try # pattern (ComicVine style)
            cleaned = re.split(
                r'(#\d+)\s*[:\-\u2013\u2014]\s*.+',
                raw_title, maxsplit=1
            )
            if len(cleaned) > 1:
                return cleaned[0] + cleaned[1]
            return raw_title

        def run_scan(self):
            try:
                files = sorted([f for f in os.listdir(self.selected_directory) if f.lower().endswith(".cbz")])
                self.root.after(0, self.safe_clear_tree)

                scan_mode = self.setting_scan_mode.get()
                pad = self.setting_num_padding.get()
                source = self.setting_online_source.get()
                use_source_fmt = self.setting_use_source_format.get()

                for i, filename in enumerate(files):
                    if not self.is_running:
                        break

                    self.root.after(0, lambda i=i, t=len(files):
                        self.status_lbl.config(text=f"Scanning {i+1} of {t}\u2026", fg=ACCENT_BLUE))

                    series_guess, vol_num_raw, type_str = parse_filename(filename)

                    try:
                        vol_num = str(int(vol_num_raw)).zfill(pad)
                    except ValueError:
                        vol_num = vol_num_raw

                    # Online lookup
                    online_series = None
                    online_raw_title = None
                    online_subtitle = None
                    online_orig_sep = " - "
                    if scan_mode in ("both", "online"):
                        try:
                            if source == "comicvine":
                                def _cv_status(text, color):
                                    self.root.after(0, lambda: self.status_lbl.config(text=text, fg=color))
                                online_series, online_raw_title, online_subtitle, online_orig_sep = \
                                    fetch_comicvine_name(series_guess, self.series_cache,
                                                        self.comicvine_api_key.get().strip(),
                                                        vol_num=vol_num_raw,
                                                        status_callback=_cv_status)
                            else:
                                online_series, online_raw_title, online_subtitle, online_orig_sep = \
                                    fetch_google_books_name(series_guess, self.series_cache)
                        except Exception as e:
                            print(f"Online lookup failed for '{series_guess}': {e}")

                    prefix = "Vol." if type_str == "Volume" else "Chapter"

                    # Build online name
                    online_name = "\u2014"
                    if online_series:
                        if use_source_fmt and online_raw_title:
                            # Use the raw title from the API, just pad the number
                            online_name = self._pad_volume_in_title(online_raw_title, vol_num)
                            # Handle subtitle stripping if subtitles are disabled
                            if not self.setting_include_subtitle.get():
                                online_name = self._strip_subtitle_from_title(online_name)
                            online_name += ".cbz"
                        else:
                            # Standardized format (old behavior), or ComicVine fallback
                            online_name = f"{online_series}, {prefix} {vol_num}"
                            if self.setting_include_subtitle.get() and online_subtitle:
                                sep_choice = self.setting_sub_separator.get()
                                if sep_choice == "colon":
                                    sep = ": "
                                elif sep_choice == "source":
                                    sep = online_orig_sep or " - "
                                else:
                                    sep = " - "
                                online_name += f"{sep}{online_subtitle}"
                            online_name += ".cbz"

                    # Build local backup name
                    backup_name = "\u2014"
                    if scan_mode in ("both", "local"):
                        backup_name = f"{series_guess}, {prefix} {vol_num}.cbz"

                    # Determine final name and status
                    if scan_mode == "online":
                        if online_series:
                            final = online_name
                            tag = "match"
                            status = "Online"
                        else:
                            final = filename
                            tag = "offline"
                            status = "No Match"
                    elif scan_mode == "local":
                        final = backup_name
                        tag = "ready"
                        status = "Ready"
                        if backup_name == filename:
                            status = "Perfect"
                            tag = "match"
                    else:
                        final = backup_name
                        tag = "ready"
                        status = "Ready"

                        if backup_name == filename:
                            status = "Perfect"
                            tag = "match"

                        if online_series:
                            final = online_name
                            if normalize(online_name) == normalize(backup_name):
                                status = "Verified"
                                tag = "match"
                            else:
                                status = "Conflict"
                                tag = "conflict"

                        if filename == final:
                            status = "Perfect"
                            tag = "match"

                    self.root.after(0, self.insert_row, filename, online_name, backup_name, final, status, tag)

                if self.is_running:
                    self.root.after(0, lambda n=len(files): self.finish_scan(n))

            except Exception as e:
                print(f"Scan Error: {e}")
                traceback.print_exc()
                if self.is_running:
                    self.root.after(0, lambda: self.status_lbl.config(text=f"Error: {e}", fg=ERROR_RED))
                    self.root.after(0, lambda: setattr(self, 'scan_in_progress', False))

        def finish_scan(self, total):
            self.scan_in_progress = False
            self.check_duplicates()
            self._enable_btn(self.btn_apply, SUCCESS_GREEN)
            self._enable_btn(self.btn_scan, ACCENT_PURPLE)
            self.status_lbl.config(text="Scan complete", fg=SUCCESS_GREEN)
            self.file_count_lbl.config(text=f"{total} file{'s' if total != 1 else ''}")

        def safe_clear_tree(self):
            self._destroy_edit()
            self.tree.delete(*self.tree.get_children())
            self.rename_data.clear()

        # ─── Table Rows ──────────────────────────────────────────────

        def insert_row(self, original, online, backup, final, status, tag):
            item_id = self.tree.insert("", tk.END, values=(original, online, backup, final, status), tags=(tag,))
            self.rename_data[item_id] = {'original': original, 'online': online, 'backup': backup, 'final': final}

        def check_duplicates(self):
            final_counts = {}
            for item_id, data in self.rename_data.items():
                if data['original'] == data['final']:
                    continue
                final_counts.setdefault(data['final'], []).append(item_id)

            for final, item_ids in final_counts.items():
                if len(item_ids) > 1:
                    for item_id in item_ids:
                        data = self.rename_data[item_id]
                        self.tree.item(item_id, values=(
                            data['original'], data['online'], data['backup'],
                            data['final'], "Duplicate"
                        ), tags=("duplicate",))

        def _update_row(self, item_id, new_final, status_text, tag):
            data = self.rename_data[item_id]
            data['final'] = new_final
            self.tree.item(item_id, values=(
                data['original'], data['online'], data['backup'], new_final, status_text
            ), tags=(tag,))
            self.check_duplicates()

        # ─── Inline Editing (Double-Click Final Column) ──────────────

        def on_double_click(self, event):
            self._destroy_edit()

            item_id = self.tree.identify_row(event.y)
            col = self.tree.identify_column(event.x)
            if not item_id or col != "#4":
                return
            if item_id not in self.rename_data:
                return

            bbox = self.tree.bbox(item_id, column="final")
            if not bbox:
                return
            x, y, w, h = bbox

            current_val = self.rename_data[item_id]['final']

            entry = tk.Entry(self.tree, font=("Segoe UI", 9),
                bg=EDIT_BG, fg="#ffffff", insertbackground="#ffffff",
                selectbackground=ACCENT_BLUE, selectforeground="white",
                relief="solid", borderwidth=1, highlightthickness=0)
            entry.insert(0, current_val)
            entry.select_range(0, tk.END)
            entry.place(x=x, y=y, width=w, height=h)
            entry.focus_set()

            self._edit_entry = entry
            self._edit_item = item_id

            def commit(evt=None):
                if self._edit_entry is None:
                    return
                new_val = self._edit_entry.get().strip()
                self._destroy_edit()
                if new_val and new_val != current_val:
                    if not new_val.lower().endswith(".cbz"):
                        new_val += ".cbz"
                    self._update_row(item_id, new_val, "Edited", "edited")
                    self.status_lbl.config(text=f"Edited: {new_val}", fg=ACCENT_BLUE)

            def cancel(evt=None):
                self._destroy_edit()

            entry.bind("<Return>", commit)
            entry.bind("<Escape>", cancel)
            entry.bind("<FocusOut>", commit)

        def _destroy_edit(self):
            if self._edit_entry is not None:
                try:
                    self._edit_entry.destroy()
                except Exception:
                    pass
                self._edit_entry = None
                self._edit_item = None

        # ─── Right-Click Toggle (Web / Local) ────────────────────────

        def on_right_click(self, event):
            item_id = self.tree.identify_row(event.y)
            if not item_id or item_id not in self.rename_data:
                return
            data = self.rename_data[item_id]
            if data['online'] == "\u2014" or data['backup'] == "\u2014":
                return

            current = data['final']
            if current == data['online']:
                new_choice = data['backup']
                self.status_lbl.config(text="Switched to Local Guess", fg=CONFLICT_YELLOW)
            else:
                new_choice = data['online']
                self.status_lbl.config(text="Switched to Web Match", fg=ACCENT_BLUE)

            self._update_row(item_id, new_choice, "Toggled", "edited")

        # ─── Apply Rename ─────────────────────────────────────────────

        def apply_rename(self):
            self._destroy_edit()

            final_names = {}
            for item_id, data in self.rename_data.items():
                if data['original'] == data['final']:
                    continue
                final = data['final']
                if final in final_names:
                    messagebox.showerror("Duplicate Error",
                        f"Multiple files would become:\n\n{final}\n\nResolve duplicates first.")
                    return
                final_names[final] = item_id

            if not final_names:
                self.status_lbl.config(text="Nothing to rename", fg=FG_DIM)
                return

            if not messagebox.askyesno("Confirm", f"Rename {len(final_names)} file(s)?"):
                return

            renamed, skipped, errors = [], [], []
            for item_id, data in self.rename_data.items():
                if data['original'] == data['final']:
                    skipped.append(data['original'])
                    continue
                try:
                    old = os.path.join(self.selected_directory, data['original'])
                    new = os.path.join(self.selected_directory, data['final'])
                    if os.path.exists(new) and old != new:
                        errors.append((data['original'], "Target already exists"))
                        continue
                    os.rename(old, new)
                    renamed.append((data['original'], data['final']))
                except OSError as e:
                    errors.append((data['original'], str(e)))

            self.show_results_dialog(renamed, skipped, errors)
            self.start_scan_thread()

        # ─── Results Dialog ───────────────────────────────────────────

        def show_results_dialog(self, renamed, skipped, errors):
            dlg = tk.Toplevel(self.root)
            dlg.title("Results")
            dlg.configure(bg=BG_DARK)
            dlg.geometry("540x440")
            dlg.resizable(True, True)
            dlg.minsize(400, 300)
            dlg.transient(self.root)
            dlg.grab_set()

            dlg.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 270
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 220
            dlg.geometry(f"+{x}+{y}")

            hdr = tk.Frame(dlg, bg=BG_PANEL, padx=24, pady=16)
            hdr.pack(fill=tk.X)

            if errors:
                icon, icon_color, title = "!", CONFLICT_YELLOW, "Completed with Errors"
            elif renamed:
                icon, icon_color, title = "\u2713", SUCCESS_GREEN, "Rename Complete"
            else:
                icon, icon_color, title = "\u2014", FG_DIM, "Nothing Changed"

            tk.Label(hdr, text=icon, bg=BG_PANEL, fg=icon_color,
                     font=("Segoe UI", 22, "bold"), width=2).pack(side=tk.LEFT, padx=(0, 12))
            tk.Label(hdr, text=title, bg=BG_PANEL, fg=FG_TEXT,
                     font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT)

            tk.Frame(dlg, bg=BORDER_COLOR, height=1).pack(fill=tk.X)

            stats = tk.Frame(dlg, bg=BG_DARK, padx=24, pady=16)
            stats.pack(fill=tk.X)

            def stat_box(parent, label, value, color):
                f = tk.Frame(parent, bg=BG_SURFACE, padx=16, pady=10)
                f.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)
                tk.Label(f, text=str(value), bg=BG_SURFACE, fg=color,
                         font=("Segoe UI", 18, "bold")).pack()
                tk.Label(f, text=label, bg=BG_SURFACE, fg=FG_DIM,
                         font=("Segoe UI", 8, "bold")).pack(pady=(2, 0))

            stat_box(stats, "RENAMED", len(renamed), SUCCESS_GREEN)
            stat_box(stats, "SKIPPED", len(skipped), FG_DIM)
            stat_box(stats, "ERRORS",  len(errors),  ERROR_RED if errors else FG_DIM)

            list_outer = tk.Frame(dlg, bg=BORDER_COLOR, padx=1, pady=1)
            list_outer.pack(fill=tk.BOTH, expand=True, padx=24, pady=(8, 0))

            list_frame = tk.Frame(list_outer, bg=TABLE_BG)
            list_frame.pack(fill=tk.BOTH, expand=True)

            text_box = tk.Text(list_frame, bg=TABLE_BG, fg=TABLE_FG, font=("Consolas", 9),
                               relief="flat", borderwidth=0, wrap=tk.NONE, padx=12, pady=10,
                               insertbackground=FG_TEXT, selectbackground=ACCENT_BLUE, cursor="arrow")
            text_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=text_box.yview,
                                         style="Dark.Vertical.TScrollbar")
            text_box.configure(yscrollcommand=text_scroll.set)
            text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            text_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            text_box.tag_configure("section", foreground=FG_DIM, font=("Segoe UI", 8, "bold"))
            text_box.tag_configure("success", foreground=SUCCESS_GREEN)
            text_box.tag_configure("error",   foreground=ERROR_RED)
            text_box.tag_configure("dim",     foreground="#555555")
            text_box.tag_configure("arrow",   foreground=ACCENT_PURPLE)

            if renamed:
                text_box.insert(tk.END, f"  RENAMED ({len(renamed)})\n", "section")
                for old, new in renamed:
                    text_box.insert(tk.END, f"    {old}\n", "dim")
                    text_box.insert(tk.END, "     \u2192  ", "arrow")
                    text_box.insert(tk.END, f"{new}\n", "success")
                text_box.insert(tk.END, "\n")

            if errors:
                text_box.insert(tk.END, f"  ERRORS ({len(errors)})\n", "section")
                for name, err in errors:
                    text_box.insert(tk.END, f"    \u2717  {name}\n", "error")
                    text_box.insert(tk.END, f"       {err}\n", "dim")
                text_box.insert(tk.END, "\n")

            if skipped:
                text_box.insert(tk.END, f"  UNCHANGED ({len(skipped)})\n", "section")
                for name in skipped:
                    text_box.insert(tk.END, f"    {name}\n", "dim")

            text_box.config(state=tk.DISABLED)

            btn_frame = tk.Frame(dlg, bg=BG_DARK, pady=14)
            btn_frame.pack(fill=tk.X)
            tk.Button(btn_frame, text="  CLOSE  ", command=dlg.destroy,
                bg=ACCENT_BLUE, fg="white", activebackground=ACCENT_HOVER, activeforeground="white",
                font=("Segoe UI", 9, "bold"), relief="flat", padx=24, pady=7,
                borderwidth=0, cursor="hand2", highlightthickness=0).pack()

    if __name__ == "__main__":
        root = tk.Tk()
        app = DarkRenamerApp(root)
        root.mainloop()

# --- CRASH CATCHER LOGIC ---
except Exception:
    error_msg = traceback.format_exc()

    with open("crash_log.txt", "w") as f:
        f.write(error_msg)

    try:
        ctypes.windll.user32.MessageBoxW(
            0,
            f"Script Crashed!\n\nCheck crash_log.txt for details.\n\nError:\n{error_msg[-500:]}",
            "CBZ Renamer Error", 0x10
        )
    except Exception:
        print(error_msg)
        input("Press Enter to exit...")