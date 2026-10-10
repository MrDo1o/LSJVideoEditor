#!/usr/bin/env python3
"""
LSJ Elite Video Editor — Windows desktop
Digital Architecture by LSJ Systems TM

Native Windows Python desktop (Tkinter). Probe/export via FFmpeg.
"""
from __future__ import annotations

import json
import os
import queue
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

import engine as nle

ROOT = Path(__file__).resolve().parent
REPO_EDITOR = ROOT.parent
GUI_DIR = ROOT / "gui"
REGISTRY_PATH = REPO_EDITOR / "EliteRegistry.json"
PROJECTS_DIR = Path.home() / "Documents" / "LSJProjects"
CACHE_DIR = Path.home() / "AppData" / "Local" / "LSJVideoEditor" / "cache"
VAULT_DIR = Path.home() / "Documents" / "LSJProjects" / "NSFW_Vault"
ICON_CANDIDATES = [
    Path.home() / "lsj_barcode_logo.ico",
    REPO_EDITOR.parent / "lsj_barcode_logo.ico",
    Path.home() / "GitHub-Repos" / "-Dokk-Command-Center-Swift" / "lsj_barcode_logo.ico",
]
def _ke_engine() -> dict:
    cfg = Path.home() / "kweenesha.toml"
    llama = os.environ.get("LLAMA_URL") or os.environ.get("LSJ_LLM_URL") or "http://127.0.0.1:8081"
    model = os.environ.get("KE_BRIDGE_MODEL") or "kweenesha-base:v2"
    max_tokens, temperature = 512, 0.55
    if cfg.is_file():
        try:
            import tomllib
            data = tomllib.loads(cfg.read_text(encoding="utf-8"))
            eng = data.get("engine") or {}
            llama = eng.get("llama_url") or llama
            model = eng.get("model") or model
            max_tokens = int(eng.get("max_tokens") or max_tokens)
            temperature = float(eng.get("temperature") or temperature)
        except Exception:
            pass
    return {
        "base": str(llama).rstrip("/").removesuffix("/v1/chat/completions"),
        "model": model,
        "max_tokens": max_tokens,
        "temperature": min(float(temperature), 0.55),
    }


KE_ENGINE = _ke_engine()
KE_SYSTEM = """You are Kweenesha (KE), LSJ Elite Video Editor on Windows.
Speak short English. Never mention One Unit.
If a production action is needed, emit one line:
TOOL: autoshot|beat|pulse|director|mashup|stabilize|upscale|captions|hdr|enhance|split|delete|export|swarm
Then one short sentence."""

KE_ACTIONS = [
    (("autoshot", "auto shot", "scene cut", "vanguard", "smart cut"), "autoshot"),
    (("beat sync", "beatsync", "beat cut"), "beat_sync"),
    (("action pulse", "pulse cut"), "action_pulse"),
    (("director",), "director_mode"),
    (("mashup", "rhythm mash"), "mashup"),
    (("stabilize", "stabilisation", "stabilization"), "stabilize_selected"),
    (("upscale",), "upscale_selected"),
    (("caption", "subtitle"), "generate_captions"),
    (("hdr", "solstice"), "hdr_master"),
    (("enhance", "proteus"), "enhance_selected"),
    (("split", "razor"), "split_at_playhead"),
    (("export mov", "export"), "master_render"),
    (("vault",), "smart_vault"),
    (("undo",), "undo"),
    (("add all", "add to timeline"), "add_all_to_timeline"),
]

VIDEO_EXTS = {
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".wmv", ".mts", ".m2ts",
    ".qt", ".3gp", ".ts", ".m2t", ".mpeg", ".mpg", ".flv", ".f4v", ".gif",
    ".hevc", ".h264", ".asf",
}
AUDIO_EXTS = {".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg", ".wma", ".opus"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

FILTER_VF = {
    "Original": None,
    "Apex": "eq=saturation=1.2:contrast=1.1",
    "Prism": "eq=saturation=1.5",
    "Lumina": "unsharp=5:5:1.0:5:5:0.0",
    "Vector": "hqdn3d=1.5:1.5:6:6",
    "Terra": "eq=saturation=1.4:contrast=1.05",
    "Obsidian": "eq=brightness=0.06:contrast=1.3",
    "Flux": "eq=saturation=0.8:contrast=1.1",
    "Helios": "colortemperature=5000",
    "Stellar": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
    "Zenith": "eq=saturation=1.1:contrast=1.2",
    "Aeon": "eq=brightness=0.05",
    "Elysium": "colortemperature=7500",
    "Halo": "gblur=sigma=1.6,eq=contrast=1.05",
    "Nova": "eq=saturation=1.5",
    "Radiant": "eq=contrast=1.45",
    "Hunter": "eq=saturation=0.6:contrast=1.4",
    "Lyric": "colortemperature=6000",
    "Aero": "hue=s=0.35,eq=contrast=1.05",
    "Elite Zoom": "scale=iw*1.25:ih*1.25,crop=iw/1.25:ih/1.25",
    "Elite Angle (Left)": "scale=iw*1.5:ih*1.5,crop=iw/1.5:ih/1.5:0:ih*0.125",
    "Elite Angle (Right)": "scale=iw*1.5:ih*1.5,crop=iw/1.5:ih/1.5:(iw-iw/1.5):ih*0.125",
    "Elite Motion (Pan)": "scale=iw*1.2:ih*1.2,crop=iw/1.2:ih/1.2:iw*0.04:ih*0.04",
}

CSS_FILTERS = {
    "Original": "none",
    "Apex": "saturate(1.2) contrast(1.1)",
    "Prism": "saturate(1.5)",
    "Lumina": "contrast(1.15) saturate(1.05)",
    "Vector": "contrast(1.05)",
    "Terra": "saturate(1.4) contrast(1.05)",
    "Obsidian": "brightness(1.1) contrast(1.3)",
    "Flux": "saturate(0.8) contrast(1.1)",
    "Helios": "sepia(0.15) saturate(1.1)",
    "Stellar": "sepia(0.35)",
    "Zenith": "saturate(1.1) contrast(1.2)",
    "Aeon": "brightness(1.08)",
    "Elysium": "hue-rotate(-8deg) saturate(1.1)",
    "Halo": "brightness(1.08) contrast(1.05)",
    "Nova": "saturate(1.5)",
    "Radiant": "contrast(1.5)",
    "Hunter": "saturate(0.6) contrast(1.4)",
    "Lyric": "sepia(0.12)",
    "Aero": "grayscale(0.4) contrast(1.05)",
    "Elite Zoom": "contrast(1.1) saturate(1.05)",
    "Elite Angle (Left)": "contrast(1.05)",
    "Elite Angle (Right)": "contrast(1.05)",
    "Elite Motion (Pan)": "contrast(1.05)",
}

DIRECTOR_FILTERS = [
    "Elite Zoom",
    "Elite Angle (Left)",
    "Elite Angle (Right)",
    "Elite Motion (Pan)",
]

DIRECTIVE_PATTERNS = [
    {
        "pattern": r"(?:make|cut)\s+(\d+)\s+(?:quiet\s+)?clips?",
        "action": "ACTION_BATCH_SPLIT_CADENCE",
        "description": "Splits timeline into discrete acoustic/thematic clips based on natural speech pauses.",
        "params": lambda m: {"target_clip_count": int(m.group(1)), "quiet": "quiet" in m.group(0).lower()}
    },
    {
        "pattern": r"split\s+this\s+in\s+half",
        "action": "ACTION_TIMELINE_BISECT",
        "description": "Splits current timeline sequence at playhead position.",
        "params": lambda m: {"split_ratio": 0.5}
    },
    {
        "pattern": r"explain\s+(?:this\s+to\s+)?(?:those\s+)?background",
        "action": "ACTION_CHAPTER_MARK",
        "description": "Inserts metadata chapter marker for background & speaker bio.",
        "params": lambda m: {"chapter_name": "Speaker Background & Dialect Profile"}
    },
    {
        "pattern": r"(?:apply|use)\s+(?:tone\s+curve|rec\.?\s*709|hdr|film\s+grain)",
        "action": "ACTION_DISPATCH_COLOR_FILTER",
        "description": "Applies calibrated Rec.709 10-bit tone mapping & silver halide grain.",
        "params": lambda m: {"filter_preset": "Solstice"}
    },
    {
        "pattern": r"(?:upscale|enhance|denoise)",
        "action": "ACTION_DISPATCH_ENHANCER",
        "description": "Dispatches 3D spatio-temporal denoiser and contrast-adaptive texture recovery.",
        "params": lambda m: {"tool": "hqdn3d_unsharp_cas", "filter": "Lumina"}
    },
    {
        "pattern": r"(?:lower|reduce|quiet)\s+(?:volume|gain|-?6\s*db)",
        "action": "ACTION_VOLUME_GAIN",
        "description": "Adjusts audio gain by -6 dB (factor 0.5) across active clips.",
        "params": lambda m: {"gain_db": -6.0, "volume": 0.5}
    }
]


def parse_voice_directives(transcript_text: str, timestamp_start: float = 0.0) -> list[dict]:
    """Extracts actionable SSK video editing directives from natural speech."""
    actions = []
    text_lower = (transcript_text or "").lower()
    for rule in DIRECTIVE_PATTERNS:
        match = re.search(rule["pattern"], text_lower)
        if match:
            actions.append({
                "timestamp_sec": timestamp_start,
                "detected_phrase": match.group(0),
                "dispatched_action": rule["action"],
                "description": rule["description"],
                "parameters": rule["params"](match),
                "status": "DISPATCHED_TO_LSJ_CORE"
            })
    return actions



def _which_tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    home = Path.home()
    local = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    roots = [
        Path(os.environ.get("FFMPEG_PATH", "")),
        Path(r"C:\ffmpeg\bin"),
        Path(r"C:\Program Files\ffmpeg\bin"),
        Path(r"C:\Program Files\Gyan\FFmpeg\bin"),
        home / "scoop" / "apps" / "ffmpeg" / "current" / "bin",
        local / "Microsoft" / "WinGet" / "Links",
    ]
    for root in roots:
        if not root or not str(root).strip() or not root.exists():
            continue
        direct = root / f"{name}.exe"
        if direct.is_file():
            return str(direct)
    return None


def resolve_ffmpeg() -> tuple[str | None, str | None]:
    return _which_tool("ffmpeg"), _which_tool("ffprobe")


def _merge_model(dest: dict, raw: dict):
    mid = raw.get("id") or f"{raw.get('shortName','x')}-{raw.get('version','1')}"
    if any(m.get("id") == mid for m in dest["models"]):
        return
    dest["models"].append({
        "id": mid,
        "rebrandedName": raw.get("rebrandedName") or (raw.get("gui") or {}).get("name") or mid,
        "originalName": raw.get("originalName") or (raw.get("gui") or {}).get("name") or mid,
        "shortName": raw.get("shortName") or mid,
        "version": str(raw.get("version") or "1"),
        "category": raw.get("category") or "Other",
        "parameters": raw.get("parameters") or raw.get("extraParameters") or [],
    })


def load_registry() -> dict:
    data = {"models": [], "video_encoders": [], "audio_codecs": []}
    sources = [REGISTRY_PATH]
    extra_dirs = [
        REPO_EDITOR,
        REPO_EDITOR / "models",
        ROOT / "models",
        PROJECTS_DIR / "models",
        Path.home() / "Documents" / "LSJProjects" / "models",
    ]
    if REGISTRY_PATH.is_file():
        try:
            loaded = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data["models"] = list(loaded.get("models") or [])
                data["video_encoders"] = list(loaded.get("video_encoders") or [])
                data["audio_codecs"] = list(loaded.get("audio_codecs") or [])
        except (OSError, json.JSONDecodeError):
            pass
    skip = {
        "eliteregistry.json", "bedrock_models.json", "arc_timeline.json",
        "bae_arc_timeline.json", "do1okp_arc_timeline.json", "do1o_quan_arc_timeline.json",
        "mega_arc_timeline.json",
    }
    for folder in extra_dirs:
        if not folder.is_dir():
            continue
        for path in folder.glob("*.json"):
            if path.name.lower() in skip:
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(raw, dict) and isinstance(raw.get("models"), list):
                for item in raw["models"]:
                    if isinstance(item, dict):
                        _merge_model(data, item)
                if raw.get("video_encoders"):
                    data["video_encoders"].extend(raw["video_encoders"])
                if raw.get("audio_codecs"):
                    data["audio_codecs"].extend(raw["audio_codecs"])
            elif isinstance(raw, dict) and (raw.get("shortName") or raw.get("extraParameters") or raw.get("gui")):
                _merge_model(data, raw)
    data["models"].sort(key=lambda m: (m.get("category") or "Z", m.get("rebrandedName") or ""))
    return data


def find_icon() -> str | None:
    for path in ICON_CANDIDATES:
        if path.is_file():
            return str(path)
    return None


class EditorAPI:
    def __init__(self):
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        VAULT_DIR.mkdir(parents=True, exist_ok=True)
        self.export_encoder = "libx264"
        self.export_audio = "aac"
        self.window = None
        self.ffmpeg, self.ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
        self.reload_registry()
        self.lock = threading.Lock()
        self._reset_project("Untitled")
        self.history: list[str] = []
        self.undo_stack: list[list[dict]] = []
        self.redo_stack: list[list[dict]] = []
        self.is_processing = False
        self.processing_progress = 0.0
        self.ai_status = "Ready"
        self.show_history = False
        self.dark_mode = True
        self.tool = "select"
        self.is_timeline_mode = True
        self.director_rhythm = 180.0
        self.export_resolution = "1920x1080"
        self.export_fps = 30
        self.current_time = 0.0
        self.current_filter = "Original"
        self.selected_clip_id = None
        self.selected_timeline_ids: list[str] = []
        self.video_track_count = 4
        self.audio_track_count = 2
        self.pixels_per_second = 24.0
        self.snap = True
        self.comparison = False
        self.mark_in = None
        self.mark_out = None
        self.clipboard = []
        self.markers = []
        self.bin_query = ""
        self.bin_kind = "all"
        self._ke_ok = False
        self._ke_ok_at = 0.0
        self._cached_ke_model = KE_ENGINE["model"]
        self._jobs: queue.Queue = queue.Queue()
        self.ui_dirty = False
        self.last_ke_reply = ""
        self.ke_log: list[str] = []
        self._load_cached_ssk_log()
        threading.Thread(target=self._autosave_loop, daemon=True).start()
        threading.Thread(target=self._ke_loop, daemon=True).start()
        threading.Thread(target=self._job_loop, daemon=True).start()
        threading.Thread(target=self.refresh_ffmpeg, daemon=True).start()

    def _reset_project(self, name: str):
        self.project_name = name
        self.clips: list[dict] = []
        self.timeline: list[dict] = []

    def _load_cached_ssk_log(self):
        """Restore prior session thoughts from on-disk thought vault."""
        log_file = CACHE_DIR / "ssk_thought_history.log"
        if not log_file.is_file():
            return
        try:
            content = log_file.read_text(encoding="utf-8")
            blocks = [b.strip() for b in content.split("---") if b.strip()]
            for block in blocks[-40:]:
                self.ke_log.append(block)
        except Exception:
            pass

    def log_thought(self, entry: str, title: str = "REASONING"):
        """Log structured reasoning token to in-memory console and persistent on-disk vault."""
        now = time.strftime("%H:%M:%S")
        formatted = f"[{now}] [SSK {title.upper()}]\n{entry}\n---\n"
        self.ke_log.insert(0, f"[{now}] [SSK {title.upper()}] {entry}")
        self.ke_log = self.ke_log[:200]
        self.ui_dirty = True
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            log_file = CACHE_DIR / "ssk_thought_history.log"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(formatted)
        except Exception:
            pass

    def dispatch_voice_action(self, action: dict) -> bool:
        """Dispatches an SSK voice directive onto the active timeline."""
        act = action.get("dispatched_action")
        params = action.get("parameters") or {}
        ts = action.get("timestamp_sec", self.current_time)
        self.log_thought(f"Executing directive {act} (at {ts:.2f}s): {action.get('detected_phrase')}", "DIRECTIVE")

        if act == "ACTION_BATCH_SPLIT_CADENCE":
            target_count = max(2, params.get("target_clip_count", 4))
            quiet = params.get("quiet", False)
            self._snapshot("Batch Split Cadence")
            targets = [self._timeline_by_id(i) for i in self.selected_timeline_ids]
            targets = [t for t in targets if t] or sorted(self.timeline, key=lambda c: c["duration"], reverse=True)[:1]
            if targets:
                clip = targets[0]
                total_dur = clip["duration"]
                step = total_dur / target_count
                if step >= 0.5:
                    orig_start = clip["start"]
                    orig_src_in = clip["sourceIn"]
                    idx = self.timeline.index(clip)
                    self.timeline.pop(idx)
                    for i in range(target_count):
                        item = dict(clip)
                        item["id"] = uuid.uuid4().hex[:8]
                        item["start"] = orig_start + i * step
                        item["sourceIn"] = orig_src_in + i * step
                        item["duration"] = step
                        item["name"] = f"{clip.get('name', 'Clip')}_pt{i+1}"
                        if quiet:
                            item["volume"] = 0.5
                        self.timeline.insert(idx + i, item)
                    self.ai_status = f"Cadence split: {target_count} clips created"
                    self.log_thought(f"Split clip into {target_count} cadence segments (quiet={quiet})", "CADENCE")
                    self.ui_dirty = True
                    return True

        elif act == "ACTION_TIMELINE_BISECT":
            self._snapshot("Timeline Bisect")
            split_t = self.current_time
            if split_t <= 0.0 and self.timeline:
                split_t = self.timeline[0]["start"] + self.timeline[0]["duration"] * 0.5
            self.split_at(split_t)
            self.ai_status = f"Bisected timeline at {split_t:.2f}s"
            self.log_thought(f"Bisected timeline sequence at {split_t:.2f}s", "BISECT")
            self.ui_dirty = True
            return True

        elif act == "ACTION_CHAPTER_MARK":
            name = params.get("chapter_name", "Chapter Marker")
            self.markers.append({"time": ts, "name": name})
            self.ai_status = f"Added marker: {name}"
            self.log_thought(f"Added chapter marker '{name}' at {ts:.2f}s", "MARKER")
            self.ui_dirty = True
            return True

        elif act == "ACTION_DISPATCH_COLOR_FILTER":
            preset = params.get("filter_preset", "Solstice")
            self.apply_filter(preset)
            self.ai_status = f"Applied filter: {preset}"
            self.log_thought(f"Applied color filter preset '{preset}'", "FILTER")
            self.ui_dirty = True
            return True

        elif act == "ACTION_DISPATCH_ENHANCER":
            filt = params.get("filter", "Lumina")
            self.apply_filter(filt)
            self.ai_status = f"Enhancer active: {filt}"
            self.log_thought(f"Dispatched enhancer with filter '{filt}'", "ENHANCE")
            self.ui_dirty = True
            return True

        elif act == "ACTION_VOLUME_GAIN":
            vol = float(params.get("volume", 0.5))
            self._snapshot("Volume Gain")
            targets = [self._timeline_by_id(i) for i in self.selected_timeline_ids]
            targets = [t for t in targets if t] or self.timeline
            for c in targets:
                c["volume"] = vol
            self.ai_status = f"Volume adjusted: {vol:.2f} (-6dB)"
            self.log_thought(f"Adjusted audio gain to {vol:.2f} (-6dB) across {len(targets)} clips", "AUDIO")
            self.ui_dirty = True
            return True

        return False

    def reload_registry(self):
        reg = load_registry()
        self.models = reg.get("models") or []
        self.encoders = [
            e for e in (reg.get("video_encoders") or [])
            if "videotoolbox" not in str(e.get("ffmpegOpts") or "").lower()
        ]
        self.codecs = reg.get("audio_codecs") or []
        self.ai_status = (
            f"Registry: {len(self.models)} models, "
            f"{len(self.encoders)} encoders, {len(self.codecs)} audio"
        )
        return self.get_state() if hasattr(self, "clips") else None

    def model_by_name(self, name: str) -> dict | None:
        return next((m for m in self.models if m.get("rebrandedName") == name or m.get("id") == name), None)

    def import_timeline_json(self, path=None):
        if not path:
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.wm_attributes("-topmost", True)
                path = filedialog.askopenfilename(
                    title="Load Elite timeline JSON",
                    initialdir=str(REPO_EDITOR),
                    filetypes=[("JSON", "*.json"), ("All files", "*.*")],
                )
                root.destroy()
            except Exception:
                path = ""
        if not path:
            return self.get_state()
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.ai_status = "Bad timeline JSON"
            return self.get_state()
        raw_clips = data.get("clips") or data.get("timeline") or data.get("timelineClips") or []
        self._snapshot(f"Load {Path(path).name}")
        added = 0
        t = max((c["start"] + c["duration"] for c in self.timeline), default=0.0)
        for raw in raw_clips:
            file_url = raw.get("fileURL") or raw.get("path") or raw.get("url") or ""
            if str(file_url).startswith("file:"):
                file_url = unquote(urlparse(file_url).path)
            media_path = Path(file_url)
            if not media_path.is_file():
                continue
            self._import_one(media_path)
            media = next((c for c in self.clips if c["path"] == str(media_path.resolve())), None)
            if not media:
                continue
            item = self._new_timeline_item(media, float(raw.get("startTime") or raw.get("start") or t), int(raw.get("track") or 0))
            item["sourceIn"] = float(raw.get("sourceIn") or raw.get("startTime") or 0)
            item["duration"] = float(raw.get("duration") or media.get("duration") or 1)
            item["filter"] = raw.get("filter") or "Original"
            item["filterParams"] = raw.get("filterParams") or {}
            self.timeline.append(item)
            t = item["start"] + item["duration"]
            added += 1
        self.ai_status = f"Loaded {added} clips from {Path(path).name}"
        return self.get_state()

    def attach(self, window):
        self.window = window

    def clip_by_id(self, clip_id: str) -> dict | None:
        return next((c for c in self.clips if c["id"] == clip_id), None)

    def _timeline_by_id(self, tid: str) -> dict | None:
        return next((c for c in self.timeline if c["id"] == tid), None)

    def _snapshot(self, action: str):
        self.undo_stack.append(json.loads(json.dumps(self.timeline)))
        self.redo_stack.clear()
        stamp = time.strftime("%H:%M:%S")
        self.history.insert(0, f"[{stamp}] {action}")
        self.history = self.history[:80]
        self.ai_status = action

    def _probe(self, path: Path) -> dict:
        clip = {
            "id": str(uuid.uuid4()),
            "path": str(path),
            "name": path.name,
            "duration": 0.0,
            "width": None,
            "height": None,
            "codec": None,
            "fps": None,
            "is_audio": path.suffix.lower() in AUDIO_EXTS,
            "has_audio": path.suffix.lower() in AUDIO_EXTS,
            "is_image": path.suffix.lower() in IMAGE_EXTS,
            "frameInterval": 1.0,
            "frameCount": 0,
            "previewPath": None,
        }
        if clip["is_image"]:
            clip["duration"] = 5.0
            return clip
        if not self.ffprobe:
            return clip
        cmd = [
            self.ffprobe, "-v", "error",
            "-print_format", "json",
            "-show_format", "-show_streams",
            str(path),
        ]
        try:
            raw = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, creationflags=_no_window())
            info = json.loads(raw.decode("utf-8", errors="ignore"))
        except (subprocess.CalledProcessError, json.JSONDecodeError, OSError):
            return clip
        fmt = info.get("format") or {}
        try:
            clip["duration"] = float(fmt.get("duration") or 0)
        except (TypeError, ValueError):
            clip["duration"] = 0.0
        video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
        if video:
            clip["width"] = int(video.get("width") or 0) or None
            clip["height"] = int(video.get("height") or 0) or None
            clip["codec"] = video.get("codec_name")
            rate = video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"
            try:
                num, den = rate.split("/")
                clip["fps"] = round(float(num) / float(den), 3) if float(den) else None
            except (ValueError, ZeroDivisionError):
                clip["fps"] = None
            clip["is_audio"] = False
        else:
            clip["is_audio"] = True
        audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
        clip["has_audio"] = bool(audio)
        return clip

    def _thumb(self, clip: dict):
        if not self.ffmpeg or clip.get("is_audio"):
            return
        dest = CACHE_DIR / f"{clip['id']}.jpg"
        if not dest.is_file():
            nle.extract_still(self.ffmpeg, clip["path"], str(dest), 0.4)
        if clip.get("is_image"):
            still = CACHE_DIR / "frames" / clip["id"]
            still.mkdir(parents=True, exist_ok=True)
            copy = still / "0001.jpg"
            if dest.is_file() and not copy.is_file():
                shutil.copy2(dest, copy)
            clip["frameInterval"] = 1.0
            clip["frameCount"] = 1
            return
        self._jobs.put(("preview", clip["id"]))

    def _job_loop(self):
        while True:
            try:
                kind, clip_id = self._jobs.get()
            except Exception:
                continue
            clip = self.clip_by_id(clip_id)
            if not clip or not self.ffmpeg:
                continue
            src = clip.get("path") or ""
            if kind == "preview":
                try:
                    quick = CACHE_DIR / "proxy" / f"{clip_id}_q.mp4"
                    if nle.make_quick_preview(self.ffmpeg, src, str(quick)):
                        clip["previewPath"] = str(quick)
                    self._jobs.put(("heavy", clip_id))
                except Exception:
                    pass
            elif kind == "heavy":
                try:
                    wave = CACHE_DIR / f"{clip_id}.wave.json"
                    if not wave.is_file():
                        samples = nle.extract_waveform(self.ffmpeg, src, 72)
                        wave.write_text(json.dumps(samples), encoding="utf-8")
                    interval, count = nle.extract_filmstrip(
                        self.ffmpeg, src, CACHE_DIR / "frames" / clip_id,
                        float(clip.get("duration") or 0),
                    )
                    clip["frameInterval"] = interval
                    clip["frameCount"] = count
                    proxy = CACHE_DIR / "proxy" / f"{clip_id}.mp4"
                    if nle.make_preview_proxy(self.ffmpeg, src, str(proxy), clip.get("codec")):
                        clip["previewPath"] = str(proxy)
                except Exception:
                    pass

    def ensure_still(self, clip_id: str, t: float) -> Path | None:
        clip = self.clip_by_id(clip_id)
        if not clip:
            return None
        src = clip.get("path") or ""
        poster = CACHE_DIR / f"{clip_id}.jpg"
        if clip.get("is_image") and Path(src).is_file():
            return Path(src)
        bucket = max(0, int(round(float(t or 0) * 2)))
        dest = CACHE_DIR / "stills" / clip_id / f"{bucket}.jpg"
        if dest.is_file() and dest.stat().st_size > 200:
            return dest
        if nle.extract_still(self.ffmpeg, src, str(dest), bucket / 2.0):
            return dest
        if poster.is_file():
            return poster
        return None

    def get_state(self):
        total = 0.0
        if self.timeline:
            total = max(c["start"] + c["duration"] for c in self.timeline)
        elif self.selected_clip_id:
            sel = self.clip_by_id(self.selected_clip_id)
            total = (sel or {}).get("duration") or 0.0
        preview = self._preview_clip()
        return {
            "projectName": self.project_name,
            "clips": self.clips,
            "timeline": self.timeline,
            "videoTrackCount": self.video_track_count,
            "audioTrackCount": self.audio_track_count,
            "selectedClipId": self.selected_clip_id,
            "selectedTimelineIds": self.selected_timeline_ids,
            "currentTime": self.current_time,
            "totalDuration": total,
            "currentFilter": self.current_filter,
            "tool": self.tool,
            "isTimelineMode": self.is_timeline_mode,
            "isProcessing": self.is_processing,
            "processingProgress": self.processing_progress,
            "aiStatus": self.ai_status,
            "history": self.history,
            "showHistory": self.show_history,
            "darkMode": self.dark_mode,
            "directorRhythm": self.director_rhythm,
            "exportResolution": self.export_resolution,
            "exportFps": self.export_fps,
            "ffmpeg": bool(self.ffmpeg and self.ffprobe),
            "ffmpegPath": self.ffmpeg or "",
            "models": [
                {
                    "id": m.get("id"),
                    "rebrandedName": m.get("rebrandedName"),
                    "category": m.get("category"),
                    "parameters": m.get("parameters") or [],
                }
                for m in self.models
            ],
            "filters": ["Original"] + [m.get("rebrandedName") for m in self.models if m.get("rebrandedName")],
            "cssFilters": CSS_FILTERS,
            "recent": self._recent(),
            "preview": preview,
            "canUndo": bool(self.undo_stack),
            "canRedo": bool(self.redo_stack),
            "pixelsPerSecond": self.pixels_per_second,
            "snap": self.snap,
            "comparison": self.comparison,
            "markIn": self.mark_in,
            "markOut": self.mark_out,
            "markers": self.markers,
            "binQuery": self.bin_query,
            "binKind": self.bin_kind,
            "keOnline": self._ke_ok,
            "keModel": self._cached_ke_model or KE_ENGINE["model"],
        }

    def poll(self):
        preview = self._preview_clip()
        return {
            "isProcessing": self.is_processing,
            "processingProgress": self.processing_progress,
            "aiStatus": self.ai_status,
            "keOnline": self._ke_ok,
            "keModel": self._cached_ke_model or KE_ENGINE["model"],
            "previewUrl": (preview or {}).get("url") or "",
            "playable": bool((preview or {}).get("playable")),
        }

    def _preview_clip(self) -> dict | None:
        media = None
        offset = self.current_time
        filt = self.current_filter
        if self.is_timeline_mode and self.timeline:
            t = self.current_time
            hits = [c for c in self.timeline if c["start"] <= t < c["start"] + c["duration"]]
            if not hits:
                hits = sorted(self.timeline, key=lambda c: c["start"])
            if hits:
                clip = hits[0]
                media = self.clip_by_id(clip["mediaId"])
                offset = clip.get("sourceIn", 0.0) + max(0.0, t - clip["start"])
                filt = clip.get("filter") or "Original"
        if media is None and self.selected_clip_id:
            media = self.clip_by_id(self.selected_clip_id)
        if not media:
            return None
        src = media.get("previewPath") or media.get("path") or ""
        has_proxy = bool(media.get("previewPath") and Path(media["previewPath"]).is_file())
        playable = has_proxy or nle.browser_playable(src, media.get("codec"))
        token = Path(media["previewPath"]).name if has_proxy else "src"
        return {
            "url": f"/media/{media['id']}?v={token}",
            "still": f"/thumb/{media['id']}.jpg",
            "scrub": f"/still/{media['id']}?t={max(0.0, offset):.2f}",
            "offset": offset,
            "playable": playable and not media.get("is_audio") and not media.get("is_image"),
            "filter": filt,
            "css": CSS_FILTERS.get(filt or "Original", "none"),
        }

    def _recent(self) -> list[dict]:
        items = []
        if not PROJECTS_DIR.is_dir():
            return items
        files = sorted(PROJECTS_DIR.glob("*.lsj"), key=lambda p: p.stat().st_mtime, reverse=True)
        for path in files[:12]:
            items.append({"name": path.stem, "path": str(path)})
        return items

    def new_project(self):
        self._reset_project("Untitled")
        self.selected_clip_id = None
        self.selected_timeline_ids = []
        self.current_time = 0.0
        self.current_filter = "Original"
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.ai_status = "New project"
        return self.get_state()

    def import_media(self, paths=None):
        if not paths:
            paths = self._open_files()
        paths = self._normalize_paths(paths)
        if not paths:
            return self.get_state()
        imported = 0
        skipped = 0
        for raw in paths:
            path = Path(raw)
            if path.is_dir():
                nested = self._collect_media(path)
                for item in nested:
                    n, s = self._import_one(item)
                    imported += n
                    skipped += s
                continue
            n, s = self._import_one(path)
            imported += n
            skipped += s
        extra = f", skipped {skipped}" if skipped else ""
        self.ai_status = f"Imported {imported} file(s){extra}"
        return self.get_state()

    def _import_one(self, path: Path) -> tuple[int, int]:
        if not path.is_file():
            return 0, 1
        suffix = path.suffix.lower()
        if suffix not in VIDEO_EXTS | AUDIO_EXTS | IMAGE_EXTS:
            return 0, 1
        resolved = str(path.resolve())
        if any(c["path"] == resolved or c["path"] == str(path) for c in self.clips):
            return 0, 1
        clip = self._probe(path)
        clip["path"] = resolved
        self.clips.append(clip)
        threading.Thread(target=self._thumb, args=(clip,), daemon=True).start()
        if self.selected_clip_id is None:
            self.selected_clip_id = clip["id"]
        return 1, 0

    @staticmethod
    def _normalize_paths(raw) -> list[str]:
        if raw is None:
            return []
        items: list[str] = []
        if isinstance(raw, (list, tuple)):
            for part in raw:
                items.extend(EditorAPI._normalize_paths(part))
            return items
        text = str(raw).strip()
        if not text:
            return []
        if "\x00" in text:
            return [p for p in text.split("\x00") if p.strip()]
        if "\n" in text or "\r" in text:
            return [p.strip() for p in text.replace("\r", "\n").split("\n") if p.strip()]
        if "|" in text and not Path(text).exists():
            return [p.strip() for p in text.split("|") if p.strip()]
        return [text]

    def _collect_media(self, folder: Path) -> list[Path]:
        found: list[Path] = []
        allowed = VIDEO_EXTS | AUDIO_EXTS | IMAGE_EXTS
        try:
            for path in folder.rglob("*"):
                if path.is_file() and path.suffix.lower() in allowed:
                    found.append(path)
                if len(found) >= 400:
                    break
        except OSError:
            pass
        return found

    def open_project(self, path=None):
        if not path:
            picked = self._open_files(project=True)
            path = picked[0] if picked else None
        if not path:
            return self.get_state()
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.ai_status = "Failed to open project"
            return self.get_state()
        self.project_name = data.get("name") or Path(path).stem
        self.clips = data.get("clips") or []
        self.timeline = data.get("timelineClips") or data.get("timeline") or []
        self.video_track_count = int(data.get("videoTrackCount") or 2)
        self.audio_track_count = int(data.get("audioTrackCount") or 1)
        for clip in self.clips:
            clip.setdefault("id", str(uuid.uuid4()))
            clip.setdefault("path", self._legacy_path(clip))
            threading.Thread(target=self._thumb, args=(clip,), daemon=True).start()
        for item in self.timeline:
            item.setdefault("id", str(uuid.uuid4()))
            if "mediaId" not in item:
                media = item.get("mediaClip") or {}
                item["mediaId"] = media.get("id")
                item["name"] = media.get("name") or item.get("name") or "Clip"
                item["start"] = float(item.get("startTime") or item.get("start") or 0)
                item["duration"] = float(item.get("duration") or 0)
                item["track"] = int(item.get("track") or 0)
                item.setdefault("sourceIn", 0.0)
        self.selected_clip_id = self.clips[0]["id"] if self.clips else None
        self.ai_status = f"Loaded {self.project_name}"
        return self.get_state()

    @staticmethod
    def _legacy_path(clip: dict) -> str:
        raw = clip.get("path") or clip.get("url") or ""
        if raw.startswith("file:"):
            parsed = urlparse(raw)
            return unquote(parsed.path.lstrip("/"))
        return raw

    def save_project(self, name=None):
        if name:
            self.project_name = name
        payload = {
            "name": self.project_name,
            "clips": self.clips,
            "timeline": self.timeline,
            "timelineClips": self.timeline,
            "videoTrackCount": self.video_track_count,
            "audioTrackCount": self.audio_track_count,
        }
        dest = PROJECTS_DIR / f"{self.project_name}.lsj"
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.ai_status = f"Saved {dest.name}"
        return self.get_state()

    def save_project_as(self):
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes("-topmost", True)
            dest = filedialog.asksaveasfilename(
                title="Save LSJ project",
                initialdir=str(PROJECTS_DIR),
                initialfile=f"{self.project_name}.lsj",
                defaultextension=".lsj",
                filetypes=[("LSJ Project", "*.lsj"), ("All files", "*.*")],
            )
            root.destroy()
        except Exception:
            dest = ""
        if not dest:
            return self.get_state()
        self.project_name = Path(dest).stem
        return self.save_project(self.project_name)

    def select_clip(self, clip_id):
        self.selected_clip_id = clip_id
        self.selected_timeline_ids = []
        clip = self.clip_by_id(clip_id)
        self.current_time = 0.0
        self.ai_status = f"Selected: {clip['name']}" if clip else "Selected media"
        return self.get_state()

    def select_timeline(self, tid, additive=False):
        if additive:
            if tid in self.selected_timeline_ids:
                self.selected_timeline_ids = [x for x in self.selected_timeline_ids if x != tid]
            else:
                self.selected_timeline_ids.append(tid)
        else:
            self.selected_timeline_ids = [tid]
        clip = self._timeline_by_id(tid)
        if clip:
            self.current_time = clip["start"]
            self.current_filter = clip.get("filter") or "Original"
            self.ai_status = f"Timeline: {clip.get('name', 'clip')}"
        return self.get_state()

    def add_to_timeline(self, clip_id, start=None, track=0):
        media = self.clip_by_id(clip_id)
        if not media:
            return self.get_state()
        self._snapshot(f"Add {media['name']}")
        if start is None:
            start = max((c["start"] + c["duration"] for c in self.timeline), default=0.0)
        item = self._new_timeline_item(media, start, track)
        self.timeline.append(item)
        self.selected_timeline_ids = [item["id"]]
        return self.get_state()

    def move_clip(self, tid, start, track):
        clip = self._timeline_by_id(tid)
        if not clip:
            return self.get_state()
        clip["start"] = max(0.0, float(start))
        max_track = self.video_track_count + self.audio_track_count - 1
        clip["track"] = max(0, min(int(track), max_track))
        return self.get_state()

    def trim_clip(self, tid, start, duration, source_in):
        clip = self._timeline_by_id(tid)
        if not clip:
            return self.get_state()
        media = self.clip_by_id(clip["mediaId"])
        max_dur = float((media or {}).get("duration") or clip["duration"])
        src = max(0.0, float(source_in))
        dur = max(0.1, float(duration))
        if src + dur > max_dur:
            dur = max(0.1, max_dur - src)
        clip["start"] = max(0.0, float(start))
        clip["duration"] = dur
        clip["sourceIn"] = src
        return self.get_state()

    def split_at(self, seconds):
        self.current_time = max(0.0, float(seconds))
        return self.split_at_playhead()

    def split_at_playhead(self):
        t = self.current_time
        targets = [c for c in self.timeline if c["start"] < t < c["start"] + c["duration"]]
        if not targets:
            self.ai_status = "Nothing to split"
            return self.get_state()
        self._snapshot("Split")
        for clip in targets:
            offset = t - clip["start"]
            if offset < 0.1 or clip["duration"] - offset < 0.1:
                continue
            right = json.loads(json.dumps(clip))
            right["id"] = str(uuid.uuid4())
            right["start"] = t
            right["duration"] = clip["duration"] - offset
            right["sourceIn"] = clip.get("sourceIn", 0.0) + offset
            clip["duration"] = offset
            self.timeline.append(right)
        return self.get_state()

    def delete_selected(self):
        if self.selected_timeline_ids:
            self._snapshot("Delete timeline clip")
            ids = set(self.selected_timeline_ids)
            self.timeline = [c for c in self.timeline if c["id"] not in ids]
            self.selected_timeline_ids = []
        elif self.selected_clip_id:
            cid = self.selected_clip_id
            self._snapshot("Remove media")
            self.clips = [c for c in self.clips if c["id"] != cid]
            self.timeline = [c for c in self.timeline if c.get("mediaId") != cid]
            self.selected_clip_id = self.clips[0]["id"] if self.clips else None
        return self.get_state()

    def undo(self):
        if not self.undo_stack:
            return self.get_state()
        self.redo_stack.append(json.loads(json.dumps(self.timeline)))
        self.timeline = self.undo_stack.pop()
        self.ai_status = "Undo"
        return self.get_state()

    def redo(self):
        if not self.redo_stack:
            return self.get_state()
        self.undo_stack.append(json.loads(json.dumps(self.timeline)))
        self.timeline = self.redo_stack.pop()
        self.ai_status = "Redo"
        return self.get_state()

    def apply_filter(self, name):
        name = name or "Original"
        self._snapshot(f"Filter: {name}")
        self.current_filter = name
        if self.selected_timeline_ids:
            for tid in self.selected_timeline_ids:
                clip = self._timeline_by_id(tid)
                if clip:
                    clip["filter"] = name
        return self.get_state()

    def update_param(self, tid, key, value):
        clip = self._timeline_by_id(tid)
        if not clip:
            return self.get_state()
        params = clip.setdefault("filterParams", {})
        params[key] = str(value)
        return self.get_state()

    def set_time(self, seconds):
        self.current_time = max(0.0, float(seconds))
        return self.get_state()

    def set_tool(self, tool):
        self.tool = "cut" if tool == "cut" else "select"
        return self.get_state()

    def toggle_timeline_mode(self):
        self.is_timeline_mode = not self.is_timeline_mode
        return self.get_state()

    def toggle_history(self):
        self.show_history = not self.show_history
        return self.get_state()

    def set_rhythm(self, value):
        self.director_rhythm = max(10.0, min(300.0, float(value)))
        return self.get_state()

    def set_export_options(self, resolution=None, fps=None):
        if resolution:
            self.export_resolution = resolution
        if fps:
            self.export_fps = int(fps)
        return self.get_state()

    def director_mode(self):
        if not self.timeline:
            self.ai_status = "Add clips to the timeline first"
            return self.get_state()
        self._snapshot("Director Mode")
        rhythm = self.director_rhythm
        rebuilt = []
        import random
        for clip in self.timeline:
            if clip["duration"] <= rhythm:
                rebuilt.append(clip)
                continue
            remaining = clip["duration"]
            cursor = clip["start"]
            source = clip.get("sourceIn", 0.0)
            while remaining > 0:
                jitter = random.uniform(-30, 30)
                chunk = min(remaining, max(30.0, rhythm + jitter))
                if chunk < 30 and rebuilt:
                    rebuilt[-1]["duration"] += remaining
                    break
                piece = json.loads(json.dumps(clip))
                piece["id"] = str(uuid.uuid4())
                piece["start"] = cursor
                piece["duration"] = chunk
                piece["sourceIn"] = source
                piece["filter"] = random.choice(DIRECTOR_FILTERS)
                rebuilt.append(piece)
                cursor += chunk
                source += chunk
                remaining -= chunk
        self.timeline = rebuilt
        self.ai_status = "Director Mode applied"
        return self.get_state()

    def _ke_loop(self):
        while True:
            try:
                mid = self._ke_model_id()
                self._ke_ok = bool(mid)
                if mid:
                    self._cached_ke_model = mid
                self._ke_ok_at = time.time()
            except Exception:
                self._ke_ok = False
            time.sleep(10)

    def _ke_online(self) -> bool:
        return self._ke_ok

    def _ke_model_id(self) -> str:
        base = KE_ENGINE["base"]
        wanted = (KE_ENGINE["model"] or "").strip()
        ids = []
        try:
            with urlopen(f"{base}/v1/models", timeout=1.2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            ids = [m.get("id") for m in data.get("data") or [] if m.get("id")]
        except Exception:
            ids = []
        if wanted and wanted in ids:
            return wanted
        if wanted:
            low = wanted.lower()
            for mid in ids:
                if low in mid.lower() or mid.lower() in low:
                    return mid
        for mid in ids:
            if "kween" in mid.lower():
                return mid
        return ids[0] if ids else wanted

    def _post_json(self, url: str, body: dict, timeout: float = 25):
        req = Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _ask_model(self, prompt: str) -> str:
        dokk = os.environ.get("DOKK_API_URL", "http://127.0.0.1:8080").rstrip("/")
        try:
            data = self._post_json(f"{dokk}/api/ke/chat", {
                "message": f"{KE_SYSTEM}\n\nEditor command: {prompt}",
                "session_id": "lsj-editor",
            }, timeout=35)
            text = (data.get("reply") or data.get("answer") or "").strip()
            if text:
                return text
        except Exception:
            pass
        try:
            data = self._post_json(f"{dokk}/api/ke/ask", {"question": prompt}, timeout=25)
            payload = data.get("payload") or data
            text = (payload.get("answer") or data.get("reply") or "").strip()
            if text:
                return text
        except Exception:
            pass
        base = KE_ENGINE["base"]
        model = self._ke_model_id()
        if not model:
            return "Kweenesha offline — Dokk :8080 and engine :8081 did not answer."
        headers = {"Content-Type": "application/json"}
        last_err = ""
        try:
            ollama = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": KE_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"num_predict": 80, "temperature": 0.4},
            }).encode("utf-8")
            req = Request("http://127.0.0.1:11434/api/chat", data=ollama, headers=headers, method="POST")
            with urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            text = ((data.get("message") or {}).get("content") or "").strip()
            if text:
                return text
        except Exception as exc:
            last_err = str(exc)
        return f"Kweenesha engine error ({model}): {last_err or 'empty reply'}"

    def _dispatch_ke_actions(self, text: str) -> list[str]:
        blob = (text or "").lower()
        acted = []
        for keys, method in KE_ACTIONS:
            if any(k in blob for k in keys):
                fn = getattr(self, method, None)
                if not fn:
                    continue
                try:
                    fn()
                    acted.append(method)
                except Exception as exc:
                    self.ke_log.insert(0, f"{method} failed: {exc}")
        for name in list(CSS_FILTERS):
            if name != "Original" and name.lower() in blob:
                self.apply_filter(name)
                acted.append(f"filter:{name}")
                break
        return acted

    def _ke_swarm(self, prompt: str):
        dokk = os.environ.get("DOKK_API_URL", "http://127.0.0.1:8080").rstrip("/")
        self.ai_status = "KE swarm executing..."
        self.ui_dirty = True
        try:
            data = self._post_json(f"{dokk}/api/ke/swarm/execute", {
                "target": self.project_name or "LSJ Video Editor",
                "objective": prompt,
            }, timeout=90)
            summary = json.dumps(data)[:240] if not isinstance(data, dict) else (
                data.get("status") or data.get("summary") or data.get("error") or "swarm ran"
            )
            self.last_ke_reply = str(summary)
            self.ke_log.insert(0, f"SWARM: {summary}")
            self.ai_status = f"KE swarm: {str(summary)[:160]}"
        except Exception as exc:
            self.ai_status = f"KE swarm failed: {exc}"
            self.ke_log.insert(0, self.ai_status)
        self.ke_log = self.ke_log[:40]
        self.is_processing = False
        self.ui_dirty = True

    def export_project(self, resolution=None, fps=None, container="mov", mastering=True):
        if not self.timeline:
            self.ai_status = "Timeline is empty"
            return self.get_state()
        if not self.ffmpeg:
            self.ai_status = "FFmpeg not found. Install Gyan.FFmpeg then relaunch."
            return self.get_state()
        if resolution:
            self.export_resolution = resolution
        if fps:
            self.export_fps = int(fps)
        container = (container or "mov").lstrip(".").lower()
        if container in {"qt", "quicktime"}:
            container = "mov"
        default_name = f"{self.project_name}_export.{container}"
        dest = ""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes("-topmost", True)
            dest = filedialog.asksaveasfilename(
                title="Export MOV",
                initialdir=str(Path.home() / "Videos"),
                initialfile=default_name,
                defaultextension=".mov",
                filetypes=[
                    ("QuickTime MOV", "*.mov"),
                    ("MPEG-4", "*.mp4"),
                    ("All files", "*.*"),
                ],
            )
            root.destroy()
        except Exception:
            dest = ""
        if not dest:
            self.ai_status = "Export canceled"
            return self.get_state()
        dest_path = Path(dest)
        if dest_path.suffix.lower() not in {".mov", ".mp4", ".qt"}:
            dest_path = dest_path.with_suffix(".mov")
        dest = str(dest_path)
        container = dest_path.suffix.lstrip(".").lower() or "mov"
        threading.Thread(
            target=self._export_worker,
            args=(dest, self.export_resolution, self.export_fps, container or "mov", mastering),
            daemon=True,
        ).start()
        self.is_processing = True
        self.processing_progress = 0.05
        self.ai_status = "Exporting Elite Master..."
        return self.get_state()

    def _export_worker(self, dest, resolution, fps, container, mastering):
        media_by_id = {c["id"]: c for c in self.clips}

        def progress(val):
            self.processing_progress = val

        enc = next((e for e in self.encoders if e.get("id") == self.export_encoder or e.get("rebrandedName") == self.export_encoder), None)
        aud = next((a for a in self.codecs if a.get("id") == self.export_audio or a.get("rebrandedName") == self.export_audio), None)
        use_reg = enc and "h264" in str(self.export_encoder).lower()
        ok, msg = nle.export_timeline(
            self.ffmpeg, self.timeline, media_by_id, dest, resolution, int(fps), mastering, progress,
            video_opts=(enc or {}).get("ffmpegOpts") if use_reg else None,
            audio_opts=(aud or {}).get("ffmpegOpts") if use_reg else None,
        )
        self.is_processing = False
        self.processing_progress = 1.0 if ok else 0.0
        self.ai_status = f"Export complete: {Path(dest).name}" if ok else f"Export failed: {msg}"

    def refresh_ffmpeg(self):
        self.ffmpeg, self.ffprobe = resolve_ffmpeg()
        self.ai_status = "FFmpeg ready" if self.ffmpeg else "FFmpeg missing"
        return self.get_state()

    def _new_timeline_item(self, media, start, track):
        return {
            "id": str(uuid.uuid4()),
            "mediaId": media["id"],
            "name": media["name"],
            "track": int(track),
            "start": max(0.0, float(start)),
            "duration": float(media["duration"] or 1.0),
            "sourceIn": 0.0,
            "filter": "Original",
            "filterParams": {},
            "transition": "None",
            "transitionDur": 0.4,
            "caption": "",
            "captionSize": 42,
            "volume": 1.0,
            "speed": 1.0,
            "opacity": 1.0,
            "scale": 1.0,
            "rotate": 0.0,
            "x": 0.0,
            "y": 0.0,
            "fadeIn": 0.0,
            "fadeOut": 0.0,
            "brightness": 0.0,
            "contrast": 1.0,
            "saturation": 1.0,
            "reversed": False,
        }

    def update_clip(self, tid, patch):
        clip = self._timeline_by_id(tid)
        if not clip or not isinstance(patch, dict):
            return self.get_state()
        numeric = {
            "volume", "speed", "opacity", "scale", "rotate", "x", "y",
            "fadeIn", "fadeOut", "brightness", "contrast", "saturation",
            "captionSize", "transitionDur", "start", "duration", "sourceIn",
        }
        for key, value in patch.items():
            if key in numeric:
                try:
                    clip[key] = float(value)
                except (TypeError, ValueError):
                    continue
            elif key == "reversed":
                clip[key] = bool(value)
            elif key in ("caption", "transition", "filter"):
                clip[key] = str(value)
        return self.get_state()

    def select_all_timeline(self):
        self.selected_timeline_ids = [c["id"] for c in self.timeline]
        self.ai_status = f"Selected {len(self.selected_timeline_ids)} timeline clips"
        return self.get_state()

    def select_all_media(self):
        self.selected_clip_id = self.clips[0]["id"] if self.clips else None
        self.ai_status = f"Media bin: {len(self.clips)} assets"
        return self.get_state()

    def deselect_all(self):
        self.selected_timeline_ids = []
        self.selected_clip_id = None
        return self.get_state()

    def copy_selected(self):
        self.clipboard = [json.loads(json.dumps(c)) for c in self.timeline if c["id"] in self.selected_timeline_ids]
        self.ai_status = f"Copied {len(self.clipboard)}"
        return self.get_state()

    def paste_clips(self):
        if not self.clipboard:
            return self.get_state()
        self._snapshot("Paste")
        cursor = self.current_time
        for item in self.clipboard:
            clone = json.loads(json.dumps(item))
            clone["id"] = str(uuid.uuid4())
            clone["start"] = cursor
            cursor += clone["duration"]
            self.timeline.append(clone)
        return self.get_state()

    def duplicate_selected(self):
        self.copy_selected()
        return self.paste_clips()

    def ripple_delete(self):
        if not self.selected_timeline_ids:
            return self.delete_selected()
        self._snapshot("Ripple delete")
        removed = [c for c in self.timeline if c["id"] in self.selected_timeline_ids]
        ids = set(self.selected_timeline_ids)
        self.timeline = [c for c in self.timeline if c["id"] not in ids]
        for gone in removed:
            gap = gone["duration"]
            for clip in self.timeline:
                if clip["track"] == gone["track"] and clip["start"] > gone["start"]:
                    clip["start"] = max(0.0, clip["start"] - gap)
        self.selected_timeline_ids = []
        return self.get_state()

    def detach_audio(self):
        if not self.selected_timeline_ids:
            self.ai_status = "Select a timeline clip"
            return self.get_state()
        self._snapshot("Detach audio")
        audio_track = self.video_track_count
        for tid in list(self.selected_timeline_ids):
            clip = self._timeline_by_id(tid)
            media = self.clip_by_id(clip["mediaId"]) if clip else None
            if not clip or not media or not media.get("has_audio"):
                continue
            audio = json.loads(json.dumps(clip))
            audio["id"] = str(uuid.uuid4())
            audio["track"] = audio_track
            audio["name"] = f"{clip['name']} [A]"
            self.timeline.append(audio)
            clip["volume"] = 0.0
        return self.get_state()

    def reverse_selected(self):
        self._snapshot("Reverse")
        for tid in self.selected_timeline_ids:
            clip = self._timeline_by_id(tid)
            if clip:
                clip["reversed"] = not clip.get("reversed")
        self.ai_status = "Reverse toggled"
        return self.get_state()

    def freeze_frame(self):
        if not self.selected_timeline_ids:
            return self.get_state()
        self._snapshot("Freeze frame")
        for tid in list(self.selected_timeline_ids):
            clip = self._timeline_by_id(tid)
            if not clip:
                continue
            freeze = json.loads(json.dumps(clip))
            freeze["id"] = str(uuid.uuid4())
            freeze["start"] = clip["start"] + clip["duration"]
            freeze["duration"] = 2.0
            freeze["sourceIn"] = clip.get("sourceIn", 0) + clip["duration"] - 0.04
            freeze["name"] = f"{clip['name']} [HOLD]"
            self.timeline.append(freeze)
        return self.get_state()

    def add_track(self, kind="video"):
        if kind == "audio":
            self.audio_track_count += 1
        else:
            self.video_track_count += 1
        return self.get_state()

    def set_zoom(self, pps):
        self.pixels_per_second = max(8.0, min(80.0, float(pps)))
        return self.get_state()

    def zoom_in(self):
        return self.set_zoom(self.pixels_per_second + 6)

    def zoom_out(self):
        return self.set_zoom(self.pixels_per_second - 6)

    def zoom_fit(self):
        total = max((c["start"] + c["duration"] for c in self.timeline), default=20)
        return self.set_zoom(max(8.0, min(80.0, 1100 / max(1.0, total))))

    def toggle_snap(self):
        self.snap = not self.snap
        return self.get_state()

    def toggle_comparison(self):
        self.comparison = not self.comparison
        return self.get_state()

    def mark_in_point(self):
        self.mark_in = self.current_time
        self.ai_status = f"In {self.mark_in:.2f}s"
        return self.get_state()

    def mark_out_point(self):
        self.mark_out = self.current_time
        self.ai_status = f"Out {self.mark_out:.2f}s"
        return self.get_state()

    def add_marker(self):
        self.markers.append({"time": self.current_time, "label": f"M{len(self.markers)+1}"})
        return self.get_state()

    def set_bin_filter(self, query="", kind="all"):
        self.bin_query = query or ""
        self.bin_kind = kind or "all"
        return self.get_state()

    def import_screen_recordings(self):
        roots = [
            Path.home() / "Videos" / "Captures",
            Path.home() / "OneDrive" / "Videos" / "Captures",
            Path.home() / "Videos",
            Path.home() / "Desktop",
        ]
        existing = [p for p in roots if p.is_dir()]
        start = str(existing[0]) if existing else str(Path.home() / "Videos")
        picked = self._open_files(directory=start)
        if picked:
            return self.import_media(picked)
        found = []
        for root in existing:
            for ext in VIDEO_EXTS:
                found.extend(root.glob(f"*{ext}"))
                found.extend(root.glob(f"*{ext.upper()}"))
        found = sorted({str(p) for p in found if p.is_file()}, key=lambda p: Path(p).stat().st_mtime, reverse=True)
        return self.import_media(found[:80])

    def import_folder(self):
        folder = None
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes("-topmost", True)
            picked = filedialog.askdirectory(title="Import folder of videos")
            root.destroy()
            if picked:
                folder = Path(picked)
        except Exception:
            folder = None
        if not folder:
            return self.get_state()
        return self.import_media(self._collect_media(folder))

    def add_all_to_timeline(self):
        self._snapshot("Add all media")
        t = max((c["start"] + c["duration"] for c in self.timeline), default=0.0)
        for media in self.clips:
            if media.get("is_audio"):
                item = self._new_timeline_item(media, t, self.video_track_count)
            else:
                item = self._new_timeline_item(media, t, 0)
            self.timeline.append(item)
            t += item["duration"]
        return self.get_state()

    def _import_result(self, dest, label):
        if Path(dest).is_file():
            self.import_media([dest])
            self.ai_status = label
        else:
            self.ai_status = f"Failed: {label}"
        self.is_processing = False

    def _job(self, fn, *args):
        def worker():
            try:
                fn(*args)
            except Exception as exc:
                self.is_processing = False
                self.ai_status = f"Job failed: {exc}"
        threading.Thread(target=worker, daemon=True).start()

    def autoshot(self):
        media = self.clip_by_id(self.selected_clip_id)
        if not media or not self.ffmpeg:
            self.ai_status = "Select a media clip first"
            return self.get_state()
        self.is_processing = True
        self.ai_status = "Vanguard scene detect..."

        def work():
            cuts = nle.detect_scenes(self.ffmpeg, media["path"])
            self._snapshot("AutoShot")
            if not cuts:
                self.ai_status = "No scene cuts found"
                self.is_processing = False
                return
            t0 = 0.0
            for cut in cuts:
                if cut - t0 < 0.25:
                    continue
                item = self._new_timeline_item(media, t0 if not self.timeline else max(c["start"]+c["duration"] for c in self.timeline), 0)
                item["sourceIn"] = t0
                item["duration"] = cut - t0
                item["filter"] = "Vanguard"
                self.timeline.append(item)
                t0 = cut
            self.ai_status = f"AutoShot: {len(cuts)} scenes"
            self.is_processing = False
        self._job(work)
        return self.get_state()

    def beat_sync(self):
        media = self.clip_by_id(self.selected_clip_id)
        if not media or not self.ffmpeg:
            self.ai_status = "Select media with audio"
            return self.get_state()
        self.is_processing = True
        self.ai_status = "Analyzing audio pacing..."

        def work():
            beats = nle.detect_beats(self.ffmpeg, media["path"])
            self._snapshot("Beat Sync")
            if len(beats) < 2:
                self.ai_status = "Not enough beats"
                self.is_processing = False
                return
            cursor = max((c["start"] + c["duration"] for c in self.timeline), default=0.0)
            for i, beat in enumerate(beats[:-1]):
                dur = max(0.2, beats[i + 1] - beat)
                item = self._new_timeline_item(media, cursor, 0)
                item["sourceIn"] = beat
                item["duration"] = min(dur, 2.5)
                item["filter"] = nle.DIRECTOR_FILTERS[i % len(nle.DIRECTOR_FILTERS)]
                self.timeline.append(item)
                cursor += item["duration"]
            self.ai_status = f"Beat sync: {len(beats)} hits"
            self.is_processing = False
        self._job(work)
        return self.get_state()

    def action_pulse(self):
        media = self.clip_by_id(self.selected_clip_id)
        if not media:
            self.ai_status = "Select a clip"
            return self.get_state()
        self.is_processing = True
        self.ai_status = "Action Pulse..."

        def work():
            cuts = nle.detect_scenes(self.ffmpeg, media["path"], 0.22) or []
            beats = nle.detect_beats(self.ffmpeg, media["path"])
            hits = sorted(set([round(x, 2) for x in cuts + beats]))
            self._snapshot("Action Pulse")
            cursor = max((c["start"] + c["duration"] for c in self.timeline), default=0.0)
            prev = 0.0
            for hit in hits[:40]:
                if hit - prev < 0.35:
                    continue
                item = self._new_timeline_item(media, cursor, 0)
                item["sourceIn"] = prev
                item["duration"] = min(1.6, hit - prev)
                item["filter"] = random.choice(nle.DIRECTOR_FILTERS)
                item["scale"] = 1.15
                self.timeline.append(item)
                cursor += item["duration"]
                prev = hit
            self.ai_status = f"Action Pulse: {len(hits)} hits"
            self.is_processing = False
        self._job(work)
        return self.get_state()

    def stabilize_selected(self):
        media = self.clip_by_id(self.selected_clip_id)
        if not media:
            self.ai_status = "Select media to stabilize"
            return self.get_state()
        dest = str(Path(media["path"]).with_name(Path(media["path"]).stem + "_stab.mp4"))
        self.is_processing = True
        self.ai_status = "Full-frame stabilize..."

        def work():
            ok, msg = nle.stabilize(self.ffmpeg, media["path"], dest)
            self._import_result(dest, "Stabilized" if ok else msg)
        self._job(work)
        return self.get_state()

    def upscale_selected(self, scale=2):
        media = self.clip_by_id(self.selected_clip_id)
        if not media:
            self.ai_status = "Select media to upscale"
            return self.get_state()
        dest = str(Path(media["path"]).with_name(Path(media["path"]).stem + f"_{scale}x.mp4"))
        self.is_processing = True
        self.ai_status = f"Upscale {scale}x..."

        def work():
            ok, msg = nle.upscale(self.ffmpeg, media["path"], dest, int(scale))
            self._import_result(dest, f"Upscaled {scale}x" if ok else msg)
        self._job(work)
        return self.get_state()

    def enhance_selected(self):
        media = self.clip_by_id(self.selected_clip_id)
        if not media:
            self.ai_status = "Select media to enhance"
            return self.get_state()
        dest = str(Path(media["path"]).with_name(Path(media["path"]).stem + "_enhanced.mp4"))
        self.is_processing = True
        self.ai_status = "Elite enhance..."

        def work():
            ok, msg = nle.enhance(self.ffmpeg, media["path"], dest)
            self._import_result(dest, "Enhanced" if ok else msg)
        self._job(work)
        return self.get_state()

    def hdr_master(self):
        media = self.clip_by_id(self.selected_clip_id)
        if not media:
            self.ai_status = "Select media for HDR"
            return self.get_state()
        dest = str(Path(media["path"]).with_name(Path(media["path"]).stem + "_hdr.mp4"))
        self.is_processing = True
        self.ai_status = "Solstice HDR..."

        def work():
            ok, msg = nle.apply_hdr(self.ffmpeg, media["path"], dest)
            self._import_result(dest, "HDR master" if ok else msg)
        self._job(work)
        return self.get_state()

    def generate_captions(self):
        targets = [self._timeline_by_id(i) for i in self.selected_timeline_ids]
        targets = [t for t in targets if t]
        if not targets:
            media = self.clip_by_id(self.selected_clip_id)
            if not media:
                self.ai_status = "Select a clip"
                return self.get_state()
            self.is_processing = True
            self.ai_status = "Transcribing with Sovereign Whisper..."

            def work_media():
                caps = nle.generate_captions(self.ffmpeg, media["path"])
                self._snapshot("Captions")
                self.log_thought(f"Transcribed {len(caps)} segments for '{media.get('name')}'. Zero-cloud Whisper verified.", "ASR")
                cursor = max((c["start"] + c["duration"] for c in self.timeline), default=0.0)
                dispatched = 0
                for cap in caps:
                    item = self._new_timeline_item(media, cursor, 0)
                    item["sourceIn"] = cap["start"]
                    item["duration"] = max(0.4, cap["end"] - cap["start"])
                    item["caption"] = cap["text"]
                    self.timeline.append(item)
                    cursor += item["duration"]

                    directives = parse_voice_directives(cap["text"], cap["start"])
                    for d in directives:
                        if self.dispatch_voice_action(d):
                            dispatched += 1

                status_extra = f" ({dispatched} voice directives ran)" if dispatched else ""
                self.ai_status = f"Captions: {len(caps)}{status_extra}"
                self.is_processing = False
                self.ui_dirty = True
            self._job(work_media)
            return self.get_state()
        media = self.clip_by_id(targets[0]["mediaId"])
        if not media:
            return self.get_state()
        self.is_processing = True
        self.ai_status = "Transcribing with Sovereign Whisper..."

        def work():
            caps = nle.generate_captions(self.ffmpeg, media["path"])
            self.log_thought(f"Transcribed {len(caps)} segments for selected clip '{targets[0].get('name')}'.", "ASR")
            text = " ".join(c["text"] for c in caps[:4])
            dispatched = 0
            for cap in caps:
                directives = parse_voice_directives(cap["text"], cap["start"])
                for d in directives:
                    if self.dispatch_voice_action(d):
                        dispatched += 1
            for clip in targets:
                clip["caption"] = text[:80]
            status_extra = f" ({dispatched} voice directives ran)" if dispatched else ""
            self.ai_status = f"Captions applied{status_extra}"
            self.is_processing = False
            self.ui_dirty = True
        self._job(work)
        return self.get_state()

    def mashup(self, seconds=180):
        if not self.clips:
            self.ai_status = "Import media first"
            return self.get_state()
        self._snapshot("Mashup")
        built = nle.build_mashup(self.clips, float(seconds))
        items = []
        for raw in built:
            media = self.clip_by_id(raw["mediaId"])
            if not media:
                continue
            item = self._new_timeline_item(media, raw["start"], 0)
            item["sourceIn"] = raw["sourceIn"]
            item["duration"] = raw["duration"]
            item["filter"] = raw["filter"]
            items.append(item)
        self.timeline = items
        self.ai_status = f"Mashup: {len(items)} cuts / {seconds}s"
        return self.get_state()

    def master_render(self):
        return self.export_project(self.export_resolution, self.export_fps, "mov", True)

    def smart_vault(self):
        media = self.clip_by_id(self.selected_clip_id)
        if not media:
            self.ai_status = "Select media to audit"
            return self.get_state()
        dest = VAULT_DIR / Path(media["path"]).name
        try:
            shutil.copy2(media["path"], dest)
            self.ai_status = f"Copied to vault: {dest.name}"
        except OSError as exc:
            self.ai_status = f"Vault error: {exc}"
        return self.get_state()

    def apply_transition(self, kind="Fade"):
        self._snapshot(f"Transition {kind}")
        for tid in self.selected_timeline_ids:
            clip = self._timeline_by_id(tid)
            if clip:
                clip["transition"] = kind
                clip["fadeIn"] = 0.4 if kind != "None" else 0.0
        return self.get_state()

    def ai_edit(self, prompt):
        prompt = (prompt or "").strip()
        if not prompt:
            return self.get_state()
        self.history.insert(0, f"[{time.strftime('%H:%M:%S')}] KE: {prompt}")
        self.log_thought(f"Prompt: {prompt}", "PROMPT")

        # Parse voice directives directly from prompt
        directives = parse_voice_directives(prompt, self.current_time)
        voice_ran = []
        for d in directives:
            if self.dispatch_voice_action(d):
                voice_ran.append(d["dispatched_action"])

        acted = self._dispatch_ke_actions(prompt)
        all_immediate = voice_ran + [a for a in acted if a not in voice_ran]
        want_swarm = any(w in prompt.lower() for w in ("swarm", "agent", "agents", "htn"))
        if all_immediate:
            self.ai_status = f"SSK ran: {', '.join(all_immediate)}"
            self.log_thought(f"Executed directives: {', '.join(all_immediate)}", "DISPATCH")
        else:
            self.ai_status = "SSK reasoning..."
            self.is_processing = True
        self.ui_dirty = True

        def work():
            extra = []
            try:
                text = self._ask_model(prompt)
                self.last_ke_reply = text
                extra = self._dispatch_ke_actions(text)
                spoken = "\n".join(
                    ln for ln in (text or "").splitlines() if not ln.upper().startswith("TOOL:")
                ).strip() or "Ready."
                all_acted = all_immediate + [a for a in extra if a not in all_immediate]
                suffix = f" · {', '.join(all_acted)}" if all_acted else ""
                self.ai_status = f"SSK: {spoken[:180]}{suffix}"
                self.log_thought(f"Reply: {spoken[:180]}", "REASONING")
            except Exception as exc:
                if not all_immediate:
                    self.ai_status = f"SSK failed: {exc}"
                    self.log_thought(f"Execution error: {exc}", "ERROR")
            self.is_processing = False
            self.ui_dirty = True

        self._job(work)
        if want_swarm:
            self.is_processing = True
            self._job(self._ke_swarm, prompt)
        return self.get_state()

    def _open_files(self, project=False, directory=None):
        start = directory or str(Path.home() / "Videos")
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes("-topmost", True)
            if project:
                picked = filedialog.askopenfilename(
                    title="Open LSJ project",
                    initialdir=str(PROJECTS_DIR),
                    filetypes=[("LSJ Project", "*.lsj"), ("All files", "*.*")],
                )
                root.destroy()
                return [picked] if picked else []
            picked = filedialog.askopenfilenames(
                title="Import media — hold Ctrl or Shift to select many",
                initialdir=start,
                filetypes=[
                    ("Video", "*.mp4;*.mov;*.mkv;*.m4v;*.webm;*.avi;*.wmv;*.mts;*.m2ts;*.qt;*.ts;*.mpeg;*.mpg;*.flv;*.gif"),
                    ("Screen recordings", "*.mp4;*.mov;*.mkv;*.m4v;*.webm"),
                    ("Audio", "*.mp3;*.wav;*.aac;*.m4a;*.flac;*.ogg;*.wma"),
                    ("Images", "*.jpg;*.jpeg;*.png;*.webp;*.bmp"),
                    ("All files", "*.*"),
                ],
            )
            root.destroy()
            if picked:
                return list(picked)
        except Exception:
            pass
        return []

    def _autosave_loop(self):
        while True:
            time.sleep(30)
            try:
                if self.clips or self.timeline:
                    self.save_project()
            except Exception:
                pass


def _no_window() -> int:
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def selftest() -> int:
    api = EditorAPI()
    state = api.get_state()
    assert state["projectName"] == "Untitled"
    assert state["clips"] == []
    fake = {
        "id": "clip-1",
        "path": str(Path.home() / "missing.mp4"),
        "name": "missing.mp4",
        "duration": 12.0,
        "width": 1920,
        "height": 1080,
        "codec": "h264",
        "fps": 30.0,
        "is_audio": False,
        "has_audio": True,
    }
    api.clips.append(fake)
    api.add_to_timeline("clip-1", 0, 0)
    api.set_time(4)
    api.split_at_playhead()
    assert len(api.timeline) == 2
    api.undo()
    assert len(api.timeline) == 1
    api.apply_filter("Apex")
    assert api.timeline[0]["filter"] == "Apex"
    dest = PROJECTS_DIR / "Selftest.lsj"
    api.project_name = "Selftest"
    api.save_project()
    assert dest.is_file()
    print(json.dumps({
        "ok": True,
        "ffmpeg": bool(api.ffmpeg),
        "ffprobe": bool(api.ffprobe),
        "ffmpeg_path": api.ffmpeg,
        "models": len(api.models),
        "timeline": len(api.timeline),
        "project": str(dest),
    }, indent=2))
    return 0


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    from app import run_app
    run_app()


if __name__ == "__main__":
    main()
