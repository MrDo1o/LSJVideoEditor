"""LSJ Elite Video Editor — native Python / Tkinter UI."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from PIL import Image, ImageTk

from lsj_video_editor import CACHE_DIR, EditorAPI, find_icon

BG = "#070a12"
CARD = "#0d1321"
INK = "#eef3f8"
MUTED = "#8b93a7"
CYAN = "#66e0e0"
ALERT = "#c44545"
LINE = "#1a2233"
PLAY = "#e23d3d"


class EditorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.api = EditorAPI()
        self.playing = False
        self.photos: list[ImageTk.PhotoImage] = []
        self.preview_photo = None
        self._build()
        self.refresh()
        self.root.after(400, self._tick)

    def _build(self):
        self.root.title("LSJ Elite Video Editor")
        self.root.configure(bg=BG)
        self.root.geometry("1480x920")
        self.root.minsize(1100, 720)
        icon = find_icon()
        if icon:
            try:
                self.root.iconbitmap(icon)
            except tk.TclError:
                pass
        self._style()
        self._menus()
        self._toolbar()
        self._body()
        self._filters()
        self._timeline()
        self._status()
        self.root.bind("<space>", lambda e: self.toggle_play())
        self.root.bind("b", lambda e: self._do("split_at_playhead"))
        self.root.bind("<Delete>", lambda e: self._do("delete_selected"))
        self.root.bind("<Control-i>", lambda e: self._do("import_media"))
        self.root.bind("<Control-s>", lambda e: self._do("save_project"))
        self.root.bind("<Control-e>", lambda e: self._do("export_project"))
        self.root.bind("<Control-z>", lambda e: self._do("undo"))
        self.root.bind("<Control-y>", lambda e: self._do("redo"))
        self.root.bind("<Control-n>", lambda e: self._do("new_project"))
        self.root.bind("<Control-o>", lambda e: self._do("open_project"))
        self.root.bind("<Left>", lambda e: self._do("set_time", max(0, self.api.current_time - 5)))
        self.root.bind("<Right>", lambda e: self._do("set_time", self.api.current_time + 5))

    def _style(self):
        st = ttk.Style(self.root)
        st.theme_use("clam")
        st.configure(".", background=BG, foreground=INK, fieldbackground=CARD, borderwidth=0)
        st.configure("TFrame", background=BG)
        st.configure("Card.TFrame", background=CARD)
        st.configure("TLabel", background=CARD, foreground=INK)
        st.configure("Muted.TLabel", background=CARD, foreground=MUTED)
        st.configure("Status.TLabel", background="#080c16", foreground=MUTED)
        st.configure("TButton", background=CARD, foreground=INK, padding=6)
        st.map("TButton", background=[("active", "#121a2b")])
        st.configure("Cyan.TButton", background=CYAN, foreground="#041016")
        st.configure("TEntry", fieldbackground="#0a101c", foreground=INK)
        st.configure("TCombobox", fieldbackground=CARD, foreground=INK)
        st.configure("Horizontal.TScale", background=CARD, troughcolor="#121a2b")
        st.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=INK, rowheight=22)
        st.map("Treeview", background=[("selected", "#163047")], foreground=[("selected", CYAN)])

    def _menus(self):
        bar = tk.Menu(self.root, bg=CARD, fg=INK, tearoff=0, activebackground="#121a2b")
        file_m = tk.Menu(bar, tearoff=0, bg=CARD, fg=INK)
        file_m.add_command(label="New Project", command=lambda: self._do("new_project"), accelerator="Ctrl+N")
        file_m.add_command(label="Open Project…", command=lambda: self._do("open_project"), accelerator="Ctrl+O")
        file_m.add_command(label="Import Media (many)…", command=lambda: self._do("import_media"), accelerator="Ctrl+I")
        file_m.add_command(label="Import Screen Recordings…", command=lambda: self._do("import_screen_recordings"))
        file_m.add_command(label="Import Whole Folder…", command=lambda: self._do("import_folder"))
        file_m.add_command(label="Save", command=lambda: self._do("save_project"), accelerator="Ctrl+S")
        file_m.add_command(label="Save As…", command=lambda: self._do("save_project_as"))
        file_m.add_command(label="Export MOV…", command=lambda: self._do("export_project"), accelerator="Ctrl+E")
        file_m.add_command(label="Export MP4…", command=lambda: self._do("export_project", None, None, "mp4"))
        file_m.add_separator()
        file_m.add_command(label="Load Elite Timeline JSON…", command=lambda: self._do("import_timeline_json"))
        file_m.add_command(label="Reload Model Registry", command=self._reload_models)
        bar.add_cascade(label="File", menu=file_m)
        edit_m = tk.Menu(bar, tearoff=0, bg=CARD, fg=INK)
        for lab, fn, acc in [
            ("Undo", "undo", "Ctrl+Z"),
            ("Redo", "redo", "Ctrl+Y"),
            ("Copy", "copy_selected", None),
            ("Paste", "paste_clips", None),
            ("Split at Playhead", "split_at_playhead", "B"),
            ("Delete", "delete_selected", "Del"),
            ("Ripple Delete", "ripple_delete", None),
            ("Detach Audio", "detach_audio", None),
            ("Reverse", "reverse_selected", None),
            ("Freeze Frame", "freeze_frame", None),
        ]:
            edit_m.add_command(label=lab, command=lambda f=fn: self._do(f), accelerator=acc or "")
        bar.add_cascade(label="Edit", menu=edit_m)
        ke = tk.Menu(bar, tearoff=0, bg=CARD, fg=INK)
        for lab, fn in [
            ("AutoShot", "autoshot"),
            ("Beat Sync", "beat_sync"),
            ("Action Pulse", "action_pulse"),
            ("Director Mode", "director_mode"),
            ("Mashup", "mashup"),
            ("Stabilize", "stabilize_selected"),
            ("Upscale 2x", "upscale_selected"),
            ("Enhance", "enhance_selected"),
            ("HDR Master", "hdr_master"),
            ("Captions", "generate_captions"),
            ("Master Render", "master_render"),
        ]:
            ke.add_command(label=lab, command=lambda f=fn: self._do(f))
        bar.add_cascade(label="Kweenesha", menu=ke)
        self.root.config(menu=bar)

    def _toolbar(self):
        bar = tk.Frame(self.root, bg=CARD, height=52)
        bar.pack(fill="x")
        self.proj_var = tk.StringVar(value="Untitled")
        tk.Label(bar, textvariable=self.proj_var, bg=CARD, fg=INK, font=("Segoe UI", 11, "bold")).pack(side="left", padx=12)
        tk.Label(bar, text="KWEENESHA", bg=CARD, fg=CYAN, font=("Segoe UI", 9, "bold")).pack(side="left")
        self.ke_var = tk.StringVar()
        entry = tk.Entry(bar, textvariable=self.ke_var, bg="#0a101c", fg=INK, insertbackground=INK, relief="flat")
        entry.pack(side="left", fill="x", expand=True, padx=10, ipady=5)
        entry.bind("<Return>", lambda e: self._ask_ke())
        ttk.Button(bar, text="Director", style="Cyan.TButton", command=lambda: self._do("director_mode")).pack(side="right", padx=6, pady=8)
        ttk.Button(bar, text="Export MOV", style="Cyan.TButton", command=lambda: self._do("export_project")).pack(side="right", padx=6)

    def _body(self):
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=6)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        bin_f = tk.Frame(body, bg=CARD, width=280)
        bin_f.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        top = tk.Frame(bin_f, bg=CARD)
        top.pack(fill="x", padx=8, pady=6)
        tk.Label(top, text="Media Bin", bg=CARD, fg=INK, font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(top, text="+", width=3, command=lambda: self._do("import_media")).pack(side="right")
        ttk.Button(top, text="Folder", command=lambda: self._do("import_folder")).pack(side="right", padx=4)
        self.bin_list = tk.Listbox(bin_f, bg=CARD, fg=INK, selectbackground="#163047", selectforeground=CYAN,
                                   relief="flat", highlightthickness=0, activestyle="none")
        self.bin_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.bin_list.bind("<<ListboxSelect>>", self._on_bin)
        self.bin_list.bind("<Double-Button-1>", lambda e: self._add_selected())

        mid = tk.Frame(body, bg=CARD)
        mid.grid(row=0, column=1, sticky="nsew")
        self.preview = tk.Label(mid, bg="#05070c", fg=MUTED, text="Import media to begin", compound="center")
        self.preview.pack(fill="both", expand=True)
        transport = tk.Frame(mid, bg=CARD)
        transport.pack(fill="x", pady=4)
        self.tcur = tk.Label(transport, text="0:00.00", bg=CARD, fg=MUTED, font=("Consolas", 10))
        self.tcur.pack(side="left", padx=8)
        ttk.Button(transport, text="-5", command=lambda: self._do("set_time", max(0, self.api.current_time - 5))).pack(side="left")
        self.play_btn = ttk.Button(transport, text="Play", command=self.toggle_play)
        self.play_btn.pack(side="left", padx=4)
        ttk.Button(transport, text="+5", command=lambda: self._do("set_time", self.api.current_time + 5)).pack(side="left")
        self.seek = tk.Scale(transport, from_=0, to=1000, orient="horizontal", showvalue=0,
                             bg=CARD, fg=CYAN, troughcolor="#121a2b", highlightthickness=0,
                             command=self._on_seek)
        self.seek.pack(side="left", fill="x", expand=True, padx=8)
        self.ttot = tk.Label(transport, text="0:00.00", bg=CARD, fg=MUTED, font=("Consolas", 10))
        self.ttot.pack(side="right", padx=8)

        insp = tk.Frame(body, bg=CARD, width=300)
        insp.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        tk.Label(insp, text="Inspector / Models", bg=CARD, fg=INK, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=8)
        self.insp = tk.Text(insp, bg="#0a101c", fg=INK, relief="flat", height=6, wrap="word",
                            insertbackground=INK)
        self.insp.pack(fill="x", padx=8)
        tk.Label(insp, text="KWEENESHA", bg=CARD, fg=CYAN, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
        self.ke_box = tk.Text(insp, bg="#0a101c", fg=CYAN, relief="flat", height=5, wrap="word")
        self.ke_box.pack(fill="x", padx=8)
        tk.Label(insp, text="ELITE MODELS", bg=CARD, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        cat_row = tk.Frame(insp, bg=CARD)
        cat_row.pack(fill="x", padx=8)
        self.cat_var = tk.StringVar(value="All")
        cats = ["All"] + sorted({m.get("category") or "Other" for m in self.api.models})
        self.cat_box = ttk.Combobox(cat_row, textvariable=self.cat_var, values=cats, state="readonly", width=18)
        self.cat_box.pack(side="left", fill="x", expand=True)
        self.cat_box.bind("<<ComboboxSelected>>", lambda e: self._fill_models())
        self.model_list = tk.Listbox(insp, bg="#0a101c", fg=INK, selectbackground="#163047",
                                     selectforeground=CYAN, relief="flat", height=8, highlightthickness=0)
        self.model_list.pack(fill="both", expand=True, padx=8, pady=4)
        self.model_list.bind("<<ListboxSelect>>", self._on_model)
        self.param_frame = tk.Frame(insp, bg=CARD)
        self.param_frame.pack(fill="x", padx=8, pady=(0, 6))
        self._param_scales = []
        self._fill_models()
        tools = tk.Frame(insp, bg=CARD)
        tools.pack(fill="x", padx=8, pady=(0, 8))
        for i, (lab, fn) in enumerate([
            ("AutoShot", "autoshot"), ("Beat", "beat_sync"),
            ("Pulse", "action_pulse"), ("Stabilize", "stabilize_selected"),
            ("Upscale", "upscale_selected"), ("HDR", "hdr_master"),
            ("Captions", "generate_captions"), ("Mashup", "mashup"),
        ]):
            ttk.Button(tools, text=lab, command=lambda f=fn: self._do(f)).grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
            tools.columnconfigure(i % 2, weight=1)

    def _filters(self):
        row = tk.Frame(self.root, bg=CARD)
        row.pack(fill="x", padx=8)
        tk.Label(row, text="Filter", bg=CARD, fg=MUTED).pack(side="left", padx=8)
        self.filter_var = tk.StringVar(value="Original")
        names = ["Original"] + [m.get("rebrandedName") for m in self.api.models if m.get("rebrandedName")]
        self.filter_box = ttk.Combobox(row, textvariable=self.filter_var, values=names, width=28, state="readonly")
        self.filter_box.pack(side="left", pady=6)
        self.filter_box.bind("<<ComboboxSelected>>", lambda e: self._do("apply_filter", self.filter_var.get()))
        tk.Label(row, text="Encoder", bg=CARD, fg=MUTED).pack(side="left", padx=(12, 4))
        enc_names = ["Playable H.264 (Windows/Apple)"] + [
            e.get("rebrandedName") for e in self.api.encoders if e.get("rebrandedName")
        ]
        self.enc_var = tk.StringVar(value="Playable H.264 (Windows/Apple)")
        self.api.export_encoder = "Playable H.264 (Windows/Apple)"
        self.enc_box = ttk.Combobox(row, textvariable=self.enc_var, values=enc_names, width=24, state="readonly")
        self.enc_box.pack(side="left")
        self.enc_box.bind("<<ComboboxSelected>>", lambda e: setattr(self.api, "export_encoder", self.enc_var.get()))
        ttk.Button(row, text="Select", command=lambda: self._do("set_tool", "select")).pack(side="left", padx=4)
        ttk.Button(row, text="Cut", command=lambda: self._do("set_tool", "cut")).pack(side="left")
        ttk.Button(row, text="Split", command=lambda: self._do("split_at_playhead")).pack(side="left", padx=4)
        ttk.Button(row, text="Add All", command=lambda: self._do("add_all_to_timeline")).pack(side="right", padx=8)

    def _timeline(self):
        wrap = tk.Frame(self.root, bg=CARD, height=240)
        wrap.pack(fill="x", padx=8, pady=6)
        self.canvas = tk.Canvas(wrap, bg="#0a101c", height=220, highlightthickness=0)
        sx = ttk.Scrollbar(wrap, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=sx.set)
        self.canvas.pack(fill="both", expand=True)
        sx.pack(fill="x")
        self.canvas.bind("<Button-1>", self._tl_click)
        self.canvas.bind("<B1-Motion>", self._tl_drag)

    def _status(self):
        bar = tk.Frame(self.root, bg="#080c16", height=26)
        bar.pack(fill="x", side="bottom")
        self.status = tk.Label(bar, text="Ready", bg="#080c16", fg=MUTED, anchor="w")
        self.status.pack(side="left", padx=10)
        self.ffstat = tk.Label(bar, text="", bg="#080c16", fg=CYAN, anchor="e")
        self.ffstat.pack(side="right", padx=10)

    def _do(self, name, *args):
        fn = getattr(self.api, name)
        fn(*args)
        self.refresh()

    def _ask_ke(self):
        text = self.ke_var.get().strip()
        if not text:
            return
        self.ke_var.set("")
        self.api.ai_edit(text)
        self.refresh()

    def _on_bin(self, _evt=None):
        sel = self.bin_list.curselection()
        if not sel:
            return
        clip = self.api.clips[sel[0]]
        self.api.select_clip(clip["id"])
        self.refresh()

    def _add_selected(self):
        sel = self.bin_list.curselection()
        if not sel:
            return
        self.api.add_to_timeline(self.api.clips[sel[0]]["id"])
        self.refresh()

    def _on_seek(self, val):
        total = max(0.1, self._total())
        self.api.set_time(float(val) / 1000.0 * total)
        self._draw_preview()
        self._draw_timeline()

    def toggle_play(self):
        self.playing = not self.playing
        self.play_btn.configure(text="Pause" if self.playing else "Play")

    def _total(self) -> float:
        if self.api.timeline:
            return max(c["start"] + c["duration"] for c in self.api.timeline)
        if self.api.selected_clip_id:
            c = self.api.clip_by_id(self.api.selected_clip_id)
            return (c or {}).get("duration") or 0.1
        return 0.1

    def _tick(self):
        if self.playing:
            self.api.set_time(self.api.current_time + 0.12)
            if self.api.current_time >= self._total():
                self.playing = False
                self.play_btn.configure(text="Play")
            self._draw_preview()
            self._draw_timeline()
        if getattr(self.api, "ui_dirty", False):
            self.api.ui_dirty = False
            self.refresh()
        elif self.api.is_processing:
            self.status.configure(text=self.api.ai_status)
        self.root.after(120, self._tick)

    def refresh(self):
        self.proj_var.set(self.api.project_name)
        self.status.configure(text=self.api.ai_status or "Ready")
        ke = "KE online" if self.api._ke_ok else "KE offline"
        ff = "FFmpeg" if self.api.ffmpeg else "FFmpeg missing"
        self.ffstat.configure(text=f"{ke}  ·  {ff}  ·  {len(self.api.models)} models")
        self.bin_list.delete(0, "end")
        for clip in self.api.clips:
            tag = "VID" if not clip.get("is_audio") else "AUD"
            self.bin_list.insert("end", f"[{tag}] {clip['name']}   {clip.get('duration', 0):.1f}s")
        if self.api.selected_clip_id:
            for i, c in enumerate(self.api.clips):
                if c["id"] == self.api.selected_clip_id:
                    self.bin_list.selection_set(i)
                    break
        self._draw_inspector()
        self._draw_preview()
        self._draw_timeline()
        total = self._total()
        self.seek.configure(to=1000)
        self.seek.set(int(self.api.current_time / max(0.1, total) * 1000))

    def _draw_inspector(self):
        self.insp.configure(state="normal")
        self.insp.delete("1.0", "end")
        tid = self.api.selected_timeline_ids[0] if self.api.selected_timeline_ids else None
        tc = self.api._timeline_by_id(tid) if tid else None
        mc = self.api.clip_by_id(self.api.selected_clip_id)
        if tc:
            lines = [
                f"TIMELINE CLIP",
                f"Name     {tc.get('name')}",
                f"In/Dur   {tc.get('sourceIn', 0):.2f} / {tc.get('duration', 0):.2f}s",
                f"Track    T{int(tc.get('track', 0)) + 1}",
                f"Filter   {tc.get('filter') or 'Original'}",
                f"Speed    {tc.get('speed', 1)}",
                f"Volume   {tc.get('volume', 1)}",
            ]
        elif mc:
            lines = [
                f"MEDIA ASSET",
                f"Name     {mc.get('name')}",
                f"Duration {mc.get('duration', 0):.2f}s",
                f"Size     {mc.get('width') or '-'}x{mc.get('height') or '-'}",
                f"Codec    {mc.get('codec') or '-'}",
                f"FPS      {mc.get('fps') or '-'}",
            ]
        else:
            lines = ["Select a clip in the bin or timeline."]
        self.insp.insert("1.0", "\n".join(lines))
        self.insp.configure(state="disabled")
        if hasattr(self, "ke_box"):
            self.ke_box.configure(state="normal")
            self.ke_box.delete("1.0", "end")
            log = "\n".join(self.api.ke_log[:8]) if getattr(self.api, "ke_log", None) else (self.api.last_ke_reply or "Type a command: mashup, director, swarm…")
            self.ke_box.insert("1.0", log)
            self.ke_box.configure(state="disabled")
        if tc:
            self._build_param_sliders(tc)

    def _fill_models(self):
        cat = self.cat_var.get() if hasattr(self, "cat_var") else "All"
        self.model_list.delete(0, "end")
        self._visible_models = []
        for m in self.api.models:
            if cat != "All" and (m.get("category") or "Other") != cat:
                continue
            self._visible_models.append(m)
            extra = f"  [{len(m.get('parameters') or [])}p]" if m.get("parameters") else ""
            self.model_list.insert("end", f"{m.get('rebrandedName')}{extra}")

    def _on_model(self, _evt=None):
        sel = self.model_list.curselection()
        if not sel:
            return
        model = self._visible_models[sel[0]]
        name = model.get("rebrandedName")
        self.filter_var.set(name)
        self._do("apply_filter", name)
        tid = self.api.selected_timeline_ids[0] if self.api.selected_timeline_ids else None
        tc = self.api._timeline_by_id(tid) if tid else None
        if tc:
            self._build_param_sliders(tc)

    def _build_param_sliders(self, clip: dict):
        for child in self.param_frame.winfo_children():
            child.destroy()
        self._param_scales = []
        model = self.api.model_by_name(clip.get("filter") or "")
        params = (model or {}).get("parameters") or []
        if not params:
            tk.Label(self.param_frame, text="No JSON parameters on this model", bg=CARD, fg=MUTED).pack(anchor="w")
            return
        stored = clip.get("filterParams") or {}
        for spec in params:
            name = spec.get("name") or spec.get("guiName")
            if not name:
                continue
            try:
                lo = float(spec.get("min") if spec.get("min") is not None else 0)
                hi = float(spec.get("max") if spec.get("max") is not None else 1)
                default = float(spec.get("default") if spec.get("default") is not None else lo)
            except (TypeError, ValueError):
                lo, hi, default = 0.0, 1.0, 0.0
            try:
                cur = float(stored.get(name, default))
            except (TypeError, ValueError):
                cur = default
            row = tk.Frame(self.param_frame, bg=CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=spec.get("guiName") or name, bg=CARD, fg=MUTED, width=16, anchor="w").pack(side="left")
            var = tk.DoubleVar(value=cur)
            scale = tk.Scale(row, from_=lo, to=hi, resolution=0.01, orient="horizontal",
                             variable=var, showvalue=1, bg=CARD, fg=INK, troughcolor="#121a2b",
                             highlightthickness=0, length=140)
            scale.pack(side="left", fill="x", expand=True)
            scale.configure(command=lambda v, n=name, c=clip["id"]: self.api.update_param(c, n, v))
            self._param_scales.append((name, var))

    def _reload_models(self):
        self.api.reload_registry()
        cats = ["All"] + sorted({m.get("category") or "Other" for m in self.api.models})
        self.cat_box.configure(values=cats)
        names = ["Original"] + [m.get("rebrandedName") for m in self.api.models if m.get("rebrandedName")]
        self.filter_box.configure(values=names)
        enc_names = [e.get("rebrandedName") for e in self.api.encoders if e.get("rebrandedName")]
        self.enc_box.configure(values=enc_names)
        self._fill_models()
        self.refresh()

    def _photo(self, path: Path | None, size: tuple[int, int]):
        if not path or not Path(path).is_file():
            return None
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail(size)
            ph = ImageTk.PhotoImage(img)
            self.photos.append(ph)
            if len(self.photos) > 80:
                self.photos = self.photos[-40:]
            return ph
        except Exception:
            return None

    def _draw_preview(self):
        total = self._total()
        self.tcur.configure(text=self._fmt(self.api.current_time))
        self.ttot.configure(text=self._fmt(total))
        preview = self.api._preview_clip()
        if not preview:
            self.preview.configure(image="", text="Import media to begin")
            return
        media_id = None
        if self.api.is_timeline_mode and self.api.timeline:
            t = self.api.current_time
            hits = [c for c in self.api.timeline if c["start"] <= t < c["start"] + c["duration"]]
            if hits:
                media_id = hits[0].get("mediaId")
        if media_id is None:
            media_id = self.api.selected_clip_id
        still = None
        if media_id:
            still = self.api.ensure_still(media_id, preview.get("offset") or 0)
            if still is None:
                poster = CACHE_DIR / f"{media_id}.jpg"
                still = poster if poster.is_file() else None
        photo = self._photo(still, (960, 540))
        if photo:
            self.preview_photo = photo
            self.preview.configure(image=photo, text="")
        else:
            self.preview.configure(image="", text="Building preview…")

    def _draw_timeline(self):
        c = self.canvas
        c.delete("all")
        pps = self.api.pixels_per_second
        tracks = self.api.video_track_count + self.api.audio_track_count
        total = max(self._total(), 20)
        width = max(900, int(40 + total * pps))
        height = 8 + tracks * 48
        c.configure(scrollregion=(0, 0, width, height))
        for i in range(tracks):
            y = 4 + i * 48
            label = f"V{i + 1}" if i < self.api.video_track_count else f"A{i - self.api.video_track_count + 1}"
            c.create_rectangle(36, y, width, y + 44, fill=CARD, outline=LINE)
            c.create_text(18, y + 22, text=label, fill=MUTED, font=("Segoe UI", 8))
        for clip in self.api.timeline:
            x = 36 + clip["start"] * pps
            w = max(12, clip["duration"] * pps)
            y = 6 + int(clip["track"]) * 48
            sel = clip["id"] in self.api.selected_timeline_ids
            color = "#163047" if sel else "#10202a"
            c.create_rectangle(x, y, x + w, y + 40, fill=color, outline=CYAN if sel else LINE, tags=("clip", clip["id"]))
            media = self.api.clip_by_id(clip.get("mediaId"))
            if media:
                frames = CACHE_DIR / "frames" / media["id"]
                jpgs = sorted(frames.glob("*.jpg"))[: max(1, int(w // 72))]
                for n, jpg in enumerate(jpgs):
                    ph = self._photo(jpg, (72, 40))
                    if ph:
                        c.create_image(x + 2 + n * 72, y + 20, image=ph, anchor="w", tags=("clip", clip["id"]))
            c.create_text(x + 6, y + 8, text=clip.get("name", "")[:28], fill=INK, anchor="w",
                          font=("Segoe UI", 8), tags=("clip", clip["id"]))
        px = 36 + self.api.current_time * pps
        c.create_line(px, 0, px, height, fill=PLAY, width=2)
        self._drag = None

    def _tl_click(self, ev):
        item = self.canvas.find_closest(self.canvas.canvasx(ev.x), ev.y)
        tags = self.canvas.gettags(item)
        tid = next((t for t in tags if t not in ("clip", "current")), None)
        x = self.canvas.canvasx(ev.x)
        t = max(0.0, (x - 36) / max(1.0, self.api.pixels_per_second))
        if self.api.tool == "cut":
            self.api.split_at(t)
        elif tid:
            self.api.select_timeline(tid)
            self._drag = (tid, ev.x, self.api._timeline_by_id(tid)["start"] if self.api._timeline_by_id(tid) else 0)
        else:
            self.api.set_time(t)
        self.refresh()

    def _tl_drag(self, ev):
        if not getattr(self, "_drag", None):
            return
        tid, ox, start = self._drag
        dt = (ev.x - ox) / max(1.0, self.api.pixels_per_second)
        clip = self.api._timeline_by_id(tid)
        if clip:
            self.api.move_clip(tid, start + dt, clip["track"])
            self._draw_timeline()

    @staticmethod
    def _fmt(sec: float) -> str:
        sec = max(0.0, float(sec) or 0.0)
        m = int(sec) // 60
        s = int(sec) % 60
        cs = int((sec % 1) * 100)
        return f"{m}:{s:02d}.{cs:02d}"


def run_app():
    root = tk.Tk()
    EditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    run_app()
