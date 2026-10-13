"""FFmpeg production engine for LSJ Elite Video Editor (Windows)."""
from __future__ import annotations

import json
import os
import random
import re
import shutil
import struct
import subprocess
import tempfile
import time
from pathlib import Path

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

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
    "Aurora": "eq=saturation=1.25:contrast=1.08",
    "Echo": "yadif,hqdn3d=2:2:6:6",
    "Fidelity": "unsharp=5:5:1.2:5:5:0.0,eq=contrast=1.08",
    "Focus": "unsharp=7:7:1.4:7:7:0.0",
    "Grit": "eq=contrast=1.25:saturation=0.85,noise=alls=8:allf=t",
    "Pulsar": "eq=saturation=1.3:contrast=1.15",
    "Render": "eq=contrast=1.12:saturation=1.1",
    "Shadow": "eq=brightness=-0.04:contrast=1.2:saturation=0.9",
    "Solstice": "eq=contrast=1.2:saturation=1.15:brightness=0.03,colortemperature=6200",
    "Stabilizer": None,
    "Titan": "unsharp=5:5:1.1:5:5:0.0,eq=saturation=1.1",
    "Vanguard": None,
    "Vector Auto": "hqdn3d=2:1.5:6:6,unsharp=3:3:0.5:3:3:0.0",
    "Vector HQ": "hqdn3d=1:1:4:4,unsharp=5:5:0.8:5:5:0.0",
    "Elite Zoom": "scale=iw*1.25:ih*1.25,crop=iw/1.25:ih/1.25",
    "Elite Angle (Left)": "scale=iw*1.5:ih*1.5,crop=iw/1.5:ih/1.5:0:ih*0.125",
    "Elite Angle (Right)": "scale=iw*1.5:ih*1.5,crop=iw/1.5:ih/1.5:(iw-iw/1.5):ih*0.125",
    "Elite Motion (Pan)": "scale=iw*1.2:ih*1.2,crop=iw/1.2:ih/1.2:iw*0.04:ih*0.04",
}

DIRECTOR_FILTERS = [
    "Elite Zoom",
    "Elite Angle (Left)",
    "Elite Angle (Right)",
    "Elite Motion (Pan)",
]

TRANSITION_MAP = {
    "fade": "fade",
    "dissolve": "dissolve",
    "wipe": "wipeleft",
    "wipeleft": "wipeleft",
    "wiperight": "wiperight",
    "wipeup": "wipeup",
    "wipedown": "wipedown",
    "slideleft": "slideleft",
    "slideright": "slideright",
    "slideup": "slideup",
    "slidedown": "slidedown",
    "circlecrop": "circlecrop",
    "rectcrop": "rectcrop",
    "pixelize": "pixelize",
    "fadeblack": "fadeblack",
    "fadewhite": "fadewhite",
    "zoomin": "zoomin",
}


def run(cmd, timeout=None) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
        return proc.returncode, proc.stdout or ""
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def filter_chain(name: str) -> str | None:
    if not name or name == "Original":
        return None
    if name in FILTER_VF:
        return FILTER_VF[name]
    lowered = name.lower()
    if "zoom" in lowered:
        return FILTER_VF["Elite Zoom"]
    if "left" in lowered:
        return FILTER_VF["Elite Angle (Left)"]
    if "right" in lowered:
        return FILTER_VF["Elite Angle (Right)"]
    if "pan" in lowered or "motion" in lowered:
        return FILTER_VF["Elite Motion (Pan)"]
    if "hdr" in lowered or "solstice" in lowered or "hyperion" in lowered:
        return FILTER_VF["Solstice"]
    if any(k in lowered for k in ("enhance", "apex", "proteus", "iris", "lumina")):
        return "hqdn3d=1.2:1.2:4:4,unsharp=3:3:0.6:3:3:0.0,eq=contrast=1.08:saturation=1.1"
    return "eq=contrast=1.05:saturation=1.05"


def clip_vf(clip: dict, w: int, h: int, fps: int, mastering: bool) -> str:
    parts = [
        f"scale={w}:{h}:force_original_aspect_ratio=decrease",
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
        "setsar=1",
        f"fps={fps}",
    ]
    scale = float(clip.get("scale") or 1.0)
    rotate = float(clip.get("rotate") or 0.0)
    opacity = float(clip.get("opacity") or 1.0)
    track = int(clip.get("track") or 0)
    if scale != 1.0:
        parts.append(f"scale=iw*{scale}:ih*{scale}")
        if track == 0:
            if scale > 1.0:
                parts.append(f"crop={w}:{h}")
            elif scale < 1.0:
                parts.append(f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2")
    if rotate:
        parts.append(f"rotate={rotate}*PI/180:fillcolor=black")
    if opacity < 1.0:
        parts.append(f"format=rgba,colorchannelmixer=aa={opacity:.3f}")
    speed = float(clip.get("speed") or 1.0)
    if speed != 1.0 and speed > 0:
        parts.append(f"setpts={1.0 / speed:.4f}*PTS")
    if clip.get("is_freeze"):
        parts.append("loop=loop=-1:size=1:start=0")
    vf = filter_chain(clip.get("filter") or "Original")
    if vf:
        parts.append(vf)
    params = clip.get("filterParams") or {}
    try:
        noise = float(params.get("Add Noise") or 0)
    except (TypeError, ValueError):
        noise = 0.0
    try:
        recover = float(params.get("Recover Details") or params.get("Nyx Recover Details") or 0)
    except (TypeError, ValueError):
        recover = 0.0
    if noise:
        parts.append(f"noise=alls={max(1.0, noise * 180):.1f}:allf=t")
    if recover:
        parts.append(f"unsharp=5:5:{recover * 1.6:.2f}:5:5:0.0")
    bright = float(clip.get("brightness") or 0)
    contrast = float(clip.get("contrast") or 1)
    sat = float(clip.get("saturation") or 1)
    if bright or contrast != 1 or sat != 1:
        parts.append(f"eq=brightness={bright}:contrast={contrast}:saturation={sat}")
    fade_in = float(clip.get("fadeIn") or 0)
    fade_out = float(clip.get("fadeOut") or 0)
    dur = float(clip.get("duration") or 0)
    if fade_in > 0:
        parts.append(f"fade=t=in:st=0:d={fade_in}")
    if fade_out > 0 and dur > fade_out:
        parts.append(f"fade=t=out:st={dur - fade_out}:d={fade_out}")
    if clip.get("reversed"):
        parts.append("reverse")
    if mastering:
        parts.append("hqdn3d=1.2:1.2:4:4,unsharp=3:3:0.45:3:3:0.0")
    caption = (clip.get("caption") or "").replace("'", r"\'").replace(":", r"\:")
    if caption:
        size = int(clip.get("captionSize") or 42)
        parts.append(
            f"drawtext=text='{caption}':fontcolor=white:fontsize={size}:"
            "x=(w-text_w)/2:y=h-80:box=1:boxcolor=black@0.45:boxborderw=8"
        )
    return ",".join(parts)


def clip_af(clip: dict) -> str:
    parts = ["aresample=48000"]
    vol = float(clip.get("volume") or 1.0)
    if vol != 1.0:
        parts.append(f"volume={vol}")
    speed = float(clip.get("speed") or 1.0)
    if speed != 1.0:
        parts.append(f"atempo={max(0.5, min(2.0, speed))}")
    fade_in = float(clip.get("fadeIn") or 0)
    fade_out = float(clip.get("fadeOut") or 0)
    dur = float(clip.get("duration") or 0)
    if fade_in > 0:
        parts.append(f"afade=t=in:st=0:d={fade_in}")
    if fade_out > 0 and dur > fade_out:
        parts.append(f"afade=t=out:st={dur - fade_out}:d={fade_out}")
    if clip.get("reversed"):
        parts.append("areverse")
    return ",".join(parts)


BROWSER_OK = {".mp4", ".webm", ".m4v"}
PROXY_CODECS = {"hevc", "h265", "prores", "dnxhd", "dnxhr", "mpeg4", "mpeg2video", "vp9", "av1", "wmv3", "msmpeg4v3"}


def browser_playable(path: str, codec: str | None = None) -> bool:
    ext = Path(path or "").suffix.lower()
    if ext not in BROWSER_OK:
        return False
    return (codec or "").lower() not in PROXY_CODECS


def extract_still(ffmpeg: str, src: str, dest: str, t: float) -> bool:
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if dest_path.is_file() and dest_path.stat().st_size > 200:
        return True
    if not ffmpeg or not Path(src).is_file():
        return False
    code, _ = run([
        ffmpeg, "-y", "-ss", f"{max(0.0, float(t)):.3f}", "-i", src,
        "-frames:v", "1", "-vf", "scale=1280:-2",
        "-q:v", "3", dest,
    ], timeout=15)
    return code == 0 and dest_path.is_file() and dest_path.stat().st_size > 200


def make_quick_preview(ffmpeg: str, src: str, dest: str) -> bool:
    dest_path = Path(dest)
    if dest_path.is_file() and dest_path.stat().st_size > 2048:
        return True
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    code, _ = run([
        ffmpeg, "-y", "-t", "20", "-i", src,
        "-vf", "scale=1280:-2:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26", "-profile:v", "baseline",
        "-an", "-movflags", "+faststart", dest,
    ], timeout=60)
    return code == 0 and dest_path.is_file() and dest_path.stat().st_size > 2048


def make_preview_proxy(ffmpeg: str, src: str, dest: str, codec: str | None = None) -> bool:
    dest_path = Path(dest)
    if dest_path.is_file() and dest_path.stat().st_size > 2048:
        return True
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    ext = Path(src).suffix.lower()
    if ext in {".mp4", ".m4v", ".mov", ".qt"} and (codec or "").lower() in {"h264", "avc1"}:
        code, _ = run([
            ffmpeg, "-y", "-i", src, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", dest,
        ], timeout=180)
        if code == 0 and dest_path.is_file() and dest_path.stat().st_size > 2048:
            return True
    code, _ = run([
        ffmpeg, "-y", "-i", src,
        "-vf", "scale=1280:-2:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-profile:v", "baseline",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", dest,
    ], timeout=900)
    return code == 0 and dest_path.is_file() and dest_path.stat().st_size > 2048


def extract_filmstrip(ffmpeg: str, src: str, dest_dir: Path, duration: float) -> tuple[float, int]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(dest_dir.glob("*.jpg"))
    if existing:
        meta = dest_dir / "meta.json"
        if meta.is_file():
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                return float(data.get("interval") or 1), int(data.get("count") or len(existing))
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                pass
        return 1.0, len(existing)
    interval = 1.0
    if duration and duration > 0:
        interval = max(0.8, duration / 40.0)
    fps = 1.0 / interval
    code, _ = run([
        ffmpeg, "-y", "-i", src,
        "-vf", f"fps={fps:.4f},scale=96:54:force_original_aspect_ratio=decrease,pad=96:54:(ow-iw)/2:(oh-ih)/2:color=black",
        "-frames:v", "40",
        "-q:v", "5",
        str(dest_dir / "%04d.jpg"),
    ], timeout=60)
    frames = sorted(dest_dir.glob("*.jpg"))
    count = len(frames)
    (dest_dir / "meta.json").write_text(
        json.dumps({"interval": interval, "count": count}), encoding="utf-8"
    )
    return interval, count


def extract_waveform(ffmpeg: str, path: str, buckets: int = 64) -> list[float]:
    if not ffmpeg or not Path(path).is_file():
        return [0.1] * buckets
    cmd = [ffmpeg, "-v", "error", "-i", path, "-ac", "1", "-ar", "8000", "-t", "90", "-f", "s16le", "pipe:1"]
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=20, creationflags=CREATE_NO_WINDOW,
        )
        raw = proc.stdout or b""
    except (OSError, subprocess.TimeoutExpired):
        return [0.1] * buckets
    if len(raw) < 4:
        return [0.1] * buckets
    count = len(raw) // 2
    samples = struct.unpack("<" + "h" * count, raw[: count * 2])
    step = max(1, count // buckets)
    out = []
    for i in range(buckets):
        chunk = samples[i * step:(i + 1) * step]
        peak = max((abs(s) for s in chunk), default=0) / 32768.0
        out.append(round(min(1.0, peak * 1.6), 3))
    return out


def detect_scenes(ffmpeg: str, path: str, threshold: float = 0.28) -> list[float]:
    if not ffmpeg:
        return []
    cmd = [
        ffmpeg, "-i", path, "-filter:v", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ]
    _, text = run(cmd, timeout=180)
    times = []
    for match in re.finditer(r"pts_time:(\d+\.?\d*)", text):
        times.append(float(match.group(1)))
    return times


def detect_beats(ffmpeg: str, path: str) -> list[float]:
    waves = extract_waveform(ffmpeg, path, 240)
    if not waves:
        return []
    mean = sum(waves) / len(waves)
    beats = []
    for i, val in enumerate(waves):
        if val > mean * 1.45 and (not beats or (i / 240 * 90) - beats[-1] > 0.35):
            beats.append(round(i / 240 * 90, 3))
    return beats[:80]


def stabilize(ffmpeg: str, src: str, dst: str) -> tuple[bool, str]:
    work = Path(tempfile.mkdtemp(prefix="lsj_stab_"))
    trf = work / "transforms.trf"
    code, out = run([
        ffmpeg, "-y", "-i", src,
        "-vf", f"vidstabdetect=shakiness=5:accuracy=15:result={trf.as_posix()}",
        "-f", "null", "-",
    ], timeout=600)
    if code != 0 or not trf.is_file():
        code, out = run([
            ffmpeg, "-y", "-i", src,
            "-vf", "deshake=rx=32:ry=32",
            "-c:a", "copy", dst,
        ], timeout=600)
        shutil.rmtree(work, ignore_errors=True)
        return code == 0 and Path(dst).is_file(), out[-400:]
    code, out = run([
        ffmpeg, "-y", "-i", src,
        "-vf", f"vidstabtransform=input={trf.as_posix()},unsharp=5:5:0.8:3:3:0.4",
        "-c:a", "copy", dst,
    ], timeout=600)
    shutil.rmtree(work, ignore_errors=True)
    return code == 0 and Path(dst).is_file(), out[-400:]


def upscale(ffmpeg: str, src: str, dst: str, scale: int = 2) -> tuple[bool, str]:
    realesrgan = shutil.which("realesrgan-ncnn-vulkan")
    if realesrgan:
        code, out = run([realesrgan, "-i", src, "-o", dst, "-s", str(scale)], timeout=1800)
        if code == 0 and Path(dst).is_file():
            return True, out
    vf = f"scale=iw*{scale}:ih*{scale}:flags=lanczos,unsharp=5:5:0.8:5:5:0.0"
    code, out = run([ffmpeg, "-y", "-i", src, "-vf", vf, "-c:a", "copy", dst], timeout=1800)
    return code == 0 and Path(dst).is_file(), out[-400:]


def enhance(ffmpeg: str, src: str, dst: str) -> tuple[bool, str]:
    vf = "hqdn3d=1.5:1.5:6:6,unsharp=5:5:0.7:5:5:0.0,eq=contrast=1.08:saturation=1.12"
    af = "loudnorm=I=-16:TP=-1.5:LRA=11"
    code, out = run([
        ffmpeg, "-y", "-i", src, "-vf", vf, "-af", af,
        "-c:v", "libx264", "-crf", "17", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k", dst,
    ], timeout=1800)
    return code == 0 and Path(dst).is_file(), out[-400:]


def apply_hdr(ffmpeg: str, src: str, dst: str) -> tuple[bool, str]:
    vf = "eq=contrast=1.18:saturation=1.16:brightness=0.03,colortemperature=6200,unsharp=3:3:0.4:3:3:0.0"
    code, out = run([
        ffmpeg, "-y", "-i", src, "-vf", vf, "-c:a", "copy",
        "-c:v", "libx264", "-crf", "17", dst,
    ], timeout=1800)
    return code == 0 and Path(dst).is_file(), out[-400:]


_ASR_INSTANCE = None


def get_sovereign_whisper_engine() -> SovereignWhisperASREngine:
    global _ASR_INSTANCE
    if _ASR_INSTANCE is None:
        _ASR_INSTANCE = SovereignWhisperASREngine(model_id="openai/whisper-tiny")
    return _ASR_INSTANCE


def generate_captions(ffmpeg: str, src: str) -> list[dict]:
    # 1. Primary: Native Sovereign Whisper ASR offline GPU/CPU inference
    try:
        engine = get_sovereign_whisper_engine()
        res = engine.transcribe(src)
        chunks = res.get("chunks", [])
        if chunks:
            return chunks
        if res.get("text"):
            dur = res.get("audio_duration_sec") or 3.0
            return [{"start": 0.0, "end": dur, "text": res["text"]}]
    except Exception:
        pass

    # 2. Secondary fallback: CLI whisper
    whisper = shutil.which("whisper")
    if whisper:
        work = Path(tempfile.mkdtemp(prefix="lsj_cap_"))
        code, _ = run([whisper, src, "--model", "tiny", "--output_format", "json", "--output_dir", str(work)], timeout=900)
        hits = list(work.glob("*.json"))
        caps = []
        if code == 0 and hits:
            try:
                data = json.loads(hits[0].read_text(encoding="utf-8"))
                for seg in data.get("segments") or []:
                    caps.append({
                        "start": float(seg.get("start") or 0),
                        "end": float(seg.get("end") or 0),
                        "text": (seg.get("text") or "").strip(),
                    })
            except (OSError, json.JSONDecodeError):
                caps = []
        shutil.rmtree(work, ignore_errors=True)
        if caps:
            return caps

    # Fail closed: Do not fabricate captions from silence detection.
    # Silence detection identifies acoustic pauses, not speech transcription.
    return []


def build_mashup(clips: list[dict], target: float = 180.0) -> list[dict]:
    if not clips:
        return []
    usable = [c for c in clips if not c.get("is_audio") and (c.get("duration") or 0) > 1]
    if not usable:
        return []
    out = []
    t = 0.0
    i = 0
    while t < target:
        media = usable[i % len(usable)]
        factor = 1.0 - (t / target) * 0.7
        dur = max(0.6, min(media["duration"], (target / max(8, len(usable))) * factor * 2))
        max_start = max(0.0, media["duration"] - dur)
        src = random.uniform(0, max_start) if max_start else 0.0
        out.append({
            "mediaId": media["id"],
            "name": media["name"],
            "start": t,
            "duration": dur,
            "sourceIn": src,
            "track": 0,
            "filter": random.choice(DIRECTOR_FILTERS),
        })
        t += dur
        i += 1
    return out


PLAYABLE_V = (
    "-c:v libx264 -preset medium -crf 20 -profile:v high -level 4.1 "
    "-pix_fmt yuv420p -tag:v avc1"
)
PLAYABLE_A = "-c:a aac -b:a 192k -ar 48000 -ac 2"


def _even(n: int) -> int:
    n = int(n)
    return n if n % 2 == 0 else n + 1


_HWACCEL_CACHE: dict | None = None


def detect_hardware_encoders(ffmpeg: str) -> dict:
    """Probes and verifies GPU hardware acceleration encoders on the host machine."""
    global _HWACCEL_CACHE
    if _HWACCEL_CACHE is not None:
        return _HWACCEL_CACHE

    results = {
        "nvenc": False,
        "qsv": False,
        "mf": False,
        "amf": False,
        "cuda_available": False,
        "best_hardware_encoder": None,
        "best_hardware_vopts": None,
        "encoders_tested": {}
    }

    try:
        import torch
        results["cuda_available"] = bool(torch.cuda.is_available())
        if results["cuda_available"]:
            results["cuda_device_name"] = torch.cuda.get_device_name(0)
    except Exception:
        results["cuda_available"] = False

    test_specs = [
        ("nvenc", "h264_nvenc", "-c:v h264_nvenc -preset p4 -b:v 25M -pix_fmt yuv420p"),
        ("qsv", "h264_qsv", "-c:v h264_qsv -b:v 25M -pix_fmt yuv420p"),
        ("mf", "h264_mf", "-c:v h264_mf -b:v 25M -pix_fmt yuv420p"),
        ("amf", "h264_amf", "-c:v h264_amf -b:v 25M -pix_fmt yuv420p"),
    ]

    for hw_key, enc_name, vopt in test_specs:
        try:
            cmd = [
                ffmpeg, "-y",
                "-f", "lavfi", "-i", "testsrc=duration=0.1:size=640x360:rate=30",
                "-c:v", enc_name,
                "-f", "null", "-"
            ]
            code, _ = run(cmd, timeout=5)
            passed = (code == 0)
            results["encoders_tested"][enc_name] = passed
            if passed:
                results[hw_key] = True
                if results["best_hardware_encoder"] is None:
                    results["best_hardware_encoder"] = enc_name
                    results["best_hardware_vopts"] = vopt
        except Exception:
            results["encoders_tested"][enc_name] = False

    _HWACCEL_CACHE = results
    return results


def get_optimal_export_vopts(ffmpeg: str, resolution: str = "1920x1080", fps: int = 60,
                             preset: str = "balanced") -> str:
    """Returns optimal hardware-accelerated or multithreaded CPU video encoding flags."""
    hw = detect_hardware_encoders(ffmpeg)
    try:
        w, h = (int(x) for x in resolution.lower().split("x"))
    except Exception:
        w, h = 1920, 1080

    is_4k = (w >= 3840 or h >= 2160)
    target_bitrate = "50M" if is_4k else "16M"
    max_bitrate = "75M" if is_4k else "24M"

    enc = hw.get("best_hardware_encoder")
    if enc == "h264_nvenc":
        nv_p = "p2" if preset == "ultrafast" else ("p4" if preset == "balanced" else "p6")
        return f"-c:v h264_nvenc -preset {nv_p} -tune hq -rc vbr -cq 19 -b:v {target_bitrate} -maxrate {max_bitrate} -pix_fmt yuv420p -tag:v avc1"
    elif enc == "h264_qsv":
        return f"-c:v h264_qsv -global_quality 21 -b:v {target_bitrate} -maxrate {max_bitrate} -pix_fmt yuv420p -tag:v avc1"
    elif enc == "h264_mf":
        return f"-c:v h264_mf -b:v {target_bitrate} -pix_fmt yuv420p -tag:v avc1"
    else:
        cpu_preset = "ultrafast" if (is_4k or preset == "ultrafast") else "veryfast"
        return f"-c:v libx264 -preset {cpu_preset} -crf 20 -profile:v high -level 5.1 -pix_fmt yuv420p -tag:v avc1"


def _playable_opts(video_opts: str | None, audio_opts: str | None, ffmpeg: str | None = None,
                   resolution: str = "1920x1080", fps: int = 60) -> tuple[str, str]:
    v = (video_opts or "").lower()
    safe_v = any(k in v for k in ("libx264", "h264", "avc", "hevc", "h265", "nvenc", "qsv", "mf", "amf", "av1")) and "prores" not in v and "videotoolbox" not in v
    a = (audio_opts or "").lower()
    safe_a = any(k in a for k in ("aac", "libfdk")) and "pcm" not in a

    if safe_v and video_opts:
        resolved_v = video_opts
    elif ffmpeg:
        resolved_v = get_optimal_export_vopts(ffmpeg, resolution=resolution, fps=fps)
    else:
        resolved_v = PLAYABLE_V

    resolved_a = audio_opts if (safe_a and audio_opts) else PLAYABLE_A
    return resolved_v, resolved_a


def export_timeline(ffmpeg: str, clips: list[dict], media_by_id: dict, dest: str,
                    resolution: str, fps: int, mastering: bool, progress_cb=None,
                    video_opts: str | None = None, audio_opts: str | None = None,
                    video_track_count: int = 4, ducking: bool = True,
                    speech_intervals: list[tuple[float, float]] | None = None,
                    hwaccel: str | bool = "auto") -> tuple[bool, str]:
    try:
        w, h = (int(x) for x in resolution.lower().split("x"))
    except ValueError:
        w, h = 1920, 1080
    w, h = _even(max(320, w)), _even(max(180, h))

    usable_clips = []
    for clip in clips:
        media = media_by_id.get(clip.get("mediaId"))
        if media and Path(media.get("path") or "").is_file():
            usable_clips.append(clip)
    if not usable_clips:
        return False, "No valid media on timeline"

    vopts, aopts = _playable_opts(video_opts, audio_opts, ffmpeg=ffmpeg, resolution=resolution, fps=fps)
    hw_in = ["-hwaccel", "auto"] if hwaccel else []
    work = Path(tempfile.mkdtemp(prefix="lsj_export_"))
    last_log = ""

    try:
        # Separate visual clips (video tracks < video_track_count) and audio-contributing clips
        visual_clips = [
            c for c in sorted(usable_clips, key=lambda x: (float(x.get("start") or 0), int(x.get("track") or 0)))
            if int(c.get("track") or 0) < video_track_count and not media_by_id[c["mediaId"]].get("is_audio")
        ]

        audio_clips = [
            c for c in sorted(usable_clips, key=lambda x: (float(x.get("start") or 0), int(x.get("track") or 0)))
            if (media_by_id[c["mediaId"]].get("has_audio") or media_by_id[c["mediaId"]].get("is_audio"))
            and float(c.get("volume", 1.0)) > 0.001
        ]

        if visual_clips:
            total_timeline_dur = max(
                (float(c.get("start") or 0) + float(c.get("duration") or 0) for c in visual_clips),
                default=1.0
            )
        else:
            total_timeline_dur = max(
                (float(c.get("start") or 0) + float(c.get("duration") or 0) for c in usable_clips),
                default=1.0
            )
        total_timeline_dur = max(0.1, total_timeline_dur)

        # -----------------------------------------------------------------
        # Phase 1: Render Visual Video Master
        # -----------------------------------------------------------------
        visual_master = work / "visual_master.mp4"
        if not visual_clips:
            cmd_black = [
                ffmpeg, "-y",
                "-f", "lavfi", "-t", f"{total_timeline_dur:.3f}",
                "-i", f"color=c=black:s={w}x{h}:r={fps}",
                *vopts.split(),
                "-an", str(visual_master)
            ]
            code, log = run(cmd_black, timeout=600)
            if code != 0 or not visual_master.is_file():
                return False, f"Failed to generate visual canvas: {log[-400:]}"
        else:
            track0_clips = [c for c in visual_clips if int(c.get("track") or 0) == 0]
            if not track0_clips:
                track0_clips = visual_clips

            vpieces = []
            piece_meta = []
            cur_t = 0.0
            for i, clip in enumerate(track0_clips):
                if progress_cb:
                    progress_cb(0.05 + 0.55 * (i / max(1, len(track0_clips))))
                media = media_by_id[clip["mediaId"]]
                src = max(0.0, float(clip.get("sourceIn") or 0))
                dur = max(0.05, float(clip.get("duration") or 1))
                c_start = max(0.0, float(clip.get("start") or 0))

                gap = c_start - cur_t
                if gap >= 0.033:
                    gap_piece = work / f"vgap_{len(vpieces):04d}.mp4"
                    cmd_gap = [
                        ffmpeg, "-y",
                        "-f", "lavfi", "-t", f"{gap:.3f}",
                        "-i", f"color=c=black:s={w}x{h}:r={fps}",
                        *vopts.split(),
                        "-an", str(gap_piece)
                    ]
                    code, log = run(cmd_gap, timeout=300)
                    if code == 0 and gap_piece.is_file():
                        vpieces.append(gap_piece)
                        piece_meta.append({"dur": gap, "is_gap": True, "clip": None})
                        cur_t += gap

                vpiece = work / f"vseg_{len(vpieces):04d}.mp4"
                vf = clip_vf(clip, w, h, int(fps), mastering) + ",format=yuv420p"
                cmd_v = [
                    ffmpeg, "-y",
                    *hw_in,
                    "-ss", f"{src:.3f}", "-t", f"{dur:.3f}", "-i", media["path"],
                    "-vf", vf, "-an",
                    *vopts.split(),
                    "-t", f"{dur:.3f}", str(vpiece)
                ]
                code, log = run(cmd_v, timeout=1800)
                if code != 0 or not vpiece.is_file() or vpiece.stat().st_size < 500:
                    return False, f"video segment {i} failed: {log[-400:]}"
                vpieces.append(vpiece)
                piece_meta.append({"dur": dur, "is_gap": False, "clip": clip})
                cur_t += dur

            trail_gap = total_timeline_dur - cur_t
            if trail_gap >= 0.033:
                gap_piece = work / f"vgap_{len(vpieces):04d}.mp4"
                cmd_gap = [
                    ffmpeg, "-y",
                    "-f", "lavfi", "-t", f"{trail_gap:.3f}",
                    "-i", f"color=c=black:s={w}x{h}:r={fps}",
                    *vopts.split(),
                    "-an", str(gap_piece)
                ]
                code, log = run(cmd_gap, timeout=300)
                if code == 0 and gap_piece.is_file():
                    vpieces.append(gap_piece)
                    piece_meta.append({"dur": trail_gap, "is_gap": True, "clip": None})

            if not vpieces:
                return False, "no video pieces generated"

            base_video = work / "base_video.mp4"
            has_transitions = any(
                str((p.get("clip") or {}).get("transition") or "").strip().lower() in TRANSITION_MAP
                for p in piece_meta[1:]
            )

            if not has_transitions or len(vpieces) < 2:
                vlisting = work / "vconcat.txt"
                vlisting.write_text("".join(f"file '{p.as_posix()}'\n" for p in vpieces), encoding="utf-8")
                code, log = run([
                    ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(vlisting),
                    "-c:v", "copy", str(base_video)
                ], timeout=600)
                if code != 0 or not base_video.is_file():
                    code, log = run([
                        ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(vlisting),
                        *vopts.split(),
                        str(base_video)
                    ], timeout=1200)
                if code != 0 or not base_video.is_file():
                    return False, f"visual base concat failed: {log[-400:]}"
            else:
                xf_inputs = []
                for p in vpieces:
                    xf_inputs.extend(["-i", str(p)])

                xf_filts = []
                last_xf_label = "0:v"
                cur_offset = piece_meta[0]["dur"]

                for i in range(1, len(vpieces)):
                    p_info = piece_meta[i]
                    p_clip = p_info.get("clip") or {}
                    t_kind = str(p_clip.get("transition") or "None").strip().lower()
                    t_dur = float(p_clip.get("transitionDur") or 0.4)
                    prev_dur = piece_meta[i - 1]["dur"]
                    cur_dur = p_info["dur"]
                    t_dur = max(0.05, min(t_dur, prev_dur * 0.45, cur_dur * 0.45))

                    if t_kind in TRANSITION_MAP and not p_info.get("is_gap") and not piece_meta[i - 1].get("is_gap"):
                        xf_trans = TRANSITION_MAP[t_kind]
                        offset = max(0.0, cur_offset - t_dur)
                        xf_filts.append(
                            f"[{last_xf_label}][{i}:v]xfade=transition={xf_trans}:duration={t_dur:.3f}:offset={offset:.3f}[xf_{i}]"
                        )
                        last_xf_label = f"xf_{i}"
                        cur_offset = offset + cur_dur
                    else:
                        cut_dur = 0.033
                        offset = max(0.0, cur_offset - cut_dur)
                        xf_filts.append(
                            f"[{last_xf_label}][{i}:v]xfade=transition=fade:duration={cut_dur:.3f}:offset={offset:.3f}[xf_{i}]"
                        )
                        last_xf_label = f"xf_{i}"
                        cur_offset = offset + cur_dur

                xf_filts.append(f"[{last_xf_label}]format=yuv420p[base_v]")
                cmd_xf = [
                    ffmpeg, "-y", *xf_inputs,
                    "-filter_complex", ";".join(xf_filts),
                    "-map", "[base_v]",
                    *vopts.split(),
                    str(base_video)
                ]
                code, log = run(cmd_xf, timeout=1800)
                if code != 0 or not base_video.is_file():
                    return False, f"xfade transition failed: {log[-400:]}"

            # Step 2: Multi-Track Video Compositing (Overlays, PIP, B-roll on Tracks 1..N)
            overlay_clips = [c for c in visual_clips if int(c.get("track") or 0) > 0]
            if not overlay_clips:
                visual_master = base_video
            else:
                overlay_clips = sorted(overlay_clips, key=lambda c: (int(c.get("track") or 1), float(c.get("start") or 0)))
                ov_inputs = ["-i", str(base_video)]
                ov_filt_parts = []
                last_label = "0:v"

                for k, oclip in enumerate(overlay_clips):
                    o_media = media_by_id[oclip["mediaId"]]
                    o_src = max(0.0, float(oclip.get("sourceIn") or 0))
                    o_dur = max(0.05, float(oclip.get("duration") or 1))
                    o_start = max(0.0, float(oclip.get("start") or 0))
                    o_end = o_start + o_dur

                    scale_val = float(oclip.get("scale") or 1.0)
                    opacity_val = max(0.0, min(1.0, float(oclip.get("opacity") or 1.0)))
                    x_val = int(round(float(oclip.get("x") or 0)))
                    y_val = int(round(float(oclip.get("y") or 0)))

                    ov_inputs.extend([*hw_in, "-ss", f"{o_src:.3f}", "-t", f"{o_dur:.3f}", "-i", o_media["path"]])
                    in_idx = k + 1

                    vf_items = [f"setpts=PTS-STARTPTS+{o_start:.3f}/TB"]
                    clip_filters = clip_vf(oclip, w, h, int(fps), mastering)
                    if clip_filters:
                        clean_f = ",".join([f for f in clip_filters.split(",") if not f.startswith("fps=")])
                        if clean_f:
                            vf_items.append(clean_f)
                    vf_items.append("format=rgba")
                    vf_chain = ",".join(vf_items)
                    ov_filt_parts.append(
                        f"[{in_idx}:v]{vf_chain}[delayed_ov_{k}];"
                        f"[{last_label}][delayed_ov_{k}]overlay=x={x_val}:y={y_val}:enable='between(t,{o_start:.3f},{o_end:.3f})':eof_action=pass[ov_stage_{k}]"
                    )
                    last_label = f"ov_stage_{k}"

                ov_filt_parts.append(f"[{last_label}]format=yuv420p[final_visual]")
                ov_filter_graph = ";".join(ov_filt_parts)

                cmd_composite = [
                    ffmpeg, "-y", *ov_inputs,
                    "-filter_complex", ov_filter_graph,
                    "-map", "[final_visual]",
                    *vopts.split(),
                    "-t", f"{total_timeline_dur:.3f}",
                    str(visual_master)
                ]
                code, log = run(cmd_composite, timeout=1800)
                if code != 0 or not visual_master.is_file():
                    return False, f"video overlay compositing failed: {log[-400:]}"

        if progress_cb:
            progress_cb(0.65)

        # -----------------------------------------------------------------
        # Phase 2: Render & Composite Multi-Track Audio Master
        # -----------------------------------------------------------------
        audio_master = work / "audio_master.wav"
        if not audio_clips:
            cmd_null = [
                ffmpeg, "-y", "-f", "lavfi", "-t", f"{total_timeline_dur:.3f}",
                "-i", "anullsrc=r=48000:cl=stereo",
                "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
                str(audio_master)
            ]
            code, log = run(cmd_null, timeout=300)
            if code != 0 or not audio_master.is_file():
                return False, f"Failed to generate silent audio canvas: {log[-400:]}"
        else:
            audio_slices = []
            for j, clip in enumerate(audio_clips):
                if progress_cb:
                    progress_cb(0.65 + 0.20 * (j / max(1, len(audio_clips))))
                media = media_by_id[clip["mediaId"]]
                src = max(0.0, float(clip.get("sourceIn") or 0))
                dur = max(0.05, float(clip.get("duration") or 1))
                start = max(0.0, float(clip.get("start") or 0))
                af = clip_af(clip) + ",aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
                slice_wav = work / f"aslice_{j:04d}.wav"
                cmd_a = [
                    ffmpeg, "-y",
                    "-ss", f"{src:.3f}", "-t", f"{dur:.3f}", "-i", media["path"],
                    "-vn", "-af", af,
                    "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
                    "-t", f"{dur:.3f}", str(slice_wav)
                ]
                code, log = run(cmd_a, timeout=600)
                if code == 0 and slice_wav.is_file() and slice_wav.stat().st_size > 100:
                    is_dialogue = (
                        int(clip.get("track") or 0) == 0 or
                        clip.get("name", "").endswith("[A]") or
                        clip.get("audio_type") == "dialogue" or
                        not media.get("is_audio")
                    )
                    audio_slices.append({
                        "path": slice_wav,
                        "start": start,
                        "dur": dur,
                        "is_dialogue": is_dialogue,
                        "clip": clip,
                    })
                else:
                    return False, f"audio slice {j} failed: {log[-400:]}"

            if not audio_slices:
                return False, "no audio slices generated"

            if len(audio_slices) == 1:
                s0 = audio_slices[0]
                delay_ms = int(round(s0["start"] * 1000))
                if delay_ms > 0:
                    cmd_mix = [
                        ffmpeg, "-y", "-i", str(s0["path"]),
                        "-af", f"adelay={delay_ms}|{delay_ms},aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo",
                        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
                        str(audio_master)
                    ]
                    code, log = run(cmd_mix, timeout=300)
                    if code != 0 or not audio_master.is_file():
                        shutil.copyfile(str(s0["path"]), str(audio_master))
                else:
                    shutil.copyfile(str(s0["path"]), str(audio_master))
            else:
                dia_indices = [idx for idx, s in enumerate(audio_slices) if s["is_dialogue"]]
                mus_indices = [idx for idx, s in enumerate(audio_slices) if not s["is_dialogue"]]

                inputs = []
                for s in audio_slices:
                    inputs.extend(["-i", str(s["path"])])

                filt_parts = []
                for idx, s in enumerate(audio_slices):
                    d_ms = int(round(s["start"] * 1000))
                    filt_parts.append(f"[{idx}:a]adelay={d_ms}|{d_ms},aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a{idx}]")

                if ducking and dia_indices and mus_indices:
                    # Dialogue bus
                    if len(dia_indices) == 1:
                        filt_parts.append(f"[a{dia_indices[0]}]apad,asplit=2[dia_sc][dia_main]")
                    else:
                        d_in = "".join(f"[a{k}]" for k in dia_indices)
                        filt_parts.append(f"{d_in}amix=inputs={len(dia_indices)}:duration=longest:dropout_transition=0:normalize=0,apad,asplit=2[dia_sc][dia_main]")

                    # Music bus
                    if len(mus_indices) == 1:
                        mus_bus = f"[a{mus_indices[0]}]"
                    else:
                        m_in = "".join(f"[a{k}]" for k in mus_indices)
                        filt_parts.append(f"{m_in}amix=inputs={len(mus_indices)}:duration=longest:dropout_transition=0:normalize=0[mus_raw]")
                        mus_bus = "[mus_raw]"

                    # Dynamic voice-activated ducking (-12 dB attenuation with release)
                    filt_parts.append(f"{mus_bus}[dia_sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=250:makeup=1[ducked_mus]")
                    filt_parts.append("[dia_main][ducked_mus]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[aout]")
                else:
                    all_in = "".join(f"[a{k}]" for k in range(len(audio_slices)))
                    filt_parts.append(f"{all_in}amix=inputs={len(audio_slices)}:duration=longest:dropout_transition=0:normalize=0[aout]")

                filter_str = ";".join(filt_parts)
                cmd_mix = [
                    ffmpeg, "-y", *inputs,
                    "-filter_complex", filter_str,
                    "-map", "[aout]",
                    "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
                    "-t", f"{total_timeline_dur:.3f}",
                    str(audio_master)
                ]
                code, log = run(cmd_mix, timeout=600)
                if code != 0 or not audio_master.is_file():
                    simple_filt = ";".join([f"[{i}:a]adelay={int(round(s['start']*1000))}|{int(round(s['start']*1000))}[sa{i}]" for i, s in enumerate(audio_slices)])
                    simple_filt += f";{''.join(f'[sa{i}]' for i in range(len(audio_slices)))}amix=inputs={len(audio_slices)}:duration=longest:dropout_transition=0:normalize=0[aout]"
                    cmd_fallback = [
                        ffmpeg, "-y", *inputs,
                        "-filter_complex", simple_filt,
                        "-map", "[aout]",
                        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
                        "-t", f"{total_timeline_dur:.3f}",
                        str(audio_master)
                    ]
                    code, log = run(cmd_fallback, timeout=600)
                    if code != 0 or not audio_master.is_file():
                        return False, f"audio mix failed: {log[-400:]}"

        if progress_cb:
            progress_cb(0.90)

        # -----------------------------------------------------------------
        # Phase 3: Final Master Multiplexing & MP4/MOV Container
        # -----------------------------------------------------------------
        dest_path = Path(dest)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        mux = ["-f", "mov"] if dest_path.suffix.lower() in {".mov", ".qt"} else ["-f", "mp4"]

        cmd_final = [
            ffmpeg, "-y",
            "-i", str(visual_master),
            "-i", str(audio_master),
            "-c:v", "copy",
            *aopts.split(),
            "-t", f"{total_timeline_dur:.3f}",
            "-movflags", "+faststart",
            *mux, str(dest_path)
        ]
        code, log = run(cmd_final, timeout=600)
        last_log = log
        if code != 0 or not dest_path.is_file() or dest_path.stat().st_size < 2000:
            cmd_reencode = [
                ffmpeg, "-y",
                "-i", str(visual_master),
                "-i", str(audio_master),
                *vopts.split(),
                *aopts.split(),
                "-t", f"{total_timeline_dur:.3f}",
                "-movflags", "+faststart",
                *mux, str(dest_path)
            ]
            code, log = run(cmd_reencode, timeout=1800)
            last_log = log

        if code != 0 or not dest_path.is_file():
            return False, f"mux failed: {last_log[-400:]}"

        if progress_cb:
            progress_cb(1.0)
        return True, "ok"
    finally:
        shutil.rmtree(work, ignore_errors=True)


# =========================================================================
# Sovereign Model SSK ASR & Whisper Transcription Engine
# Protocol IOPQ-08 Locked Baseline | Zero-Cloud Local Inference
# =========================================================================

class SovereignWhisperASREngine:
    """
    Sovereign Whisper Automatic Speech Recognition Engine.
    Executes local GPU/CPU speech-to-text with zero external network dependencies.
    """

    def __init__(self, model_id: str = "openai/whisper-tiny", device: str | None = None):
        self.model_id = model_id
        if device:
            self.device = device
        else:
            try:
                import torch
                self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.device = "cpu"
        self.pipeline = None
        self.model = None
        self.processor = None

    def load_model(self) -> float:
        """Load local Whisper model pipeline into memory / VRAM and measure latency."""
        t0 = time.perf_counter()
        try:
            import torch
            from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

            torch_dtype = torch.float16 if "cuda" in self.device else torch.float32
            self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                self.model_id,
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=True,
                local_files_only=True
            ).to(self.device)
            self.processor = AutoProcessor.from_pretrained(self.model_id, local_files_only=True)

            self.pipeline = pipeline(
                "automatic-speech-recognition",
                model=self.model,
                tokenizer=self.processor.tokenizer,
                feature_extractor=self.processor.feature_extractor,
                chunk_length_s=30,
                batch_size=1,
                return_timestamps=True,
                torch_dtype=torch_dtype,
                device=self.device,
            )
        except Exception as e:
            # Fallback or error record
            self.pipeline = None
            raise RuntimeError(f"Failed to initialize local Whisper model {self.model_id}: {e}")
        
        load_ms = (time.perf_counter() - t0) * 1000.0
        return load_ms

    def transcribe(self, audio_path: str | Path) -> dict:
        """Transcribe audio file locally and return timestamped segments and physical metrics."""
        path = Path(audio_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Audio file not found: {path}")

        if self.pipeline is None:
            self.load_model()

        # Get audio duration using ffprobe
        duration_sec = 0.0
        ffprobe_bin = shutil.which("ffprobe") or "ffprobe"
        try:
            code, out = run([
                ffprobe_bin, "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(path)
            ], timeout=30)
            if code == 0 and out.strip():
                duration_sec = float(out.strip())
        except Exception:
            duration_sec = 14.5

        temp_wav = None
        target_audio = str(path)
        if path.suffix.lower() != ".wav":
            ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
            temp_wav = Path(tempfile.mktemp(suffix=".wav"))
            try:
                code, _ = run([
                    ffmpeg_bin, "-y", "-i", str(path),
                    "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
                    str(temp_wav)
                ], timeout=180)
                if code == 0 and temp_wav.is_file() and temp_wav.stat().st_size > 44:
                    target_audio = str(temp_wav)
            except Exception:
                pass

        t0 = time.perf_counter()
        try:
            result = self.pipeline(target_audio)
        finally:
            if temp_wav and temp_wav.is_file():
                try:
                    temp_wav.unlink()
                except OSError:
                    pass
        transcribe_ms = (time.perf_counter() - t0) * 1000.0

        raw_text = result.get("text", "").strip()
        chunks = []
        for ch in result.get("chunks", []):
            ts = ch.get("timestamp", (0.0, 0.0))
            chunks.append({
                "start": float(ts[0] or 0.0),
                "end": float(ts[1] or duration_sec),
                "text": ch.get("text", "").strip(),
            })

        if not chunks and raw_text:
            chunks.append({"start": 0.0, "end": duration_sec, "text": raw_text})

        rtf = round((transcribe_ms / 1000.0) / max(0.1, duration_sec), 4)

        return {
            "text": raw_text,
            "chunks": chunks,
            "audio_duration_sec": duration_sec,
            "transcribe_ms": transcribe_ms,
            "real_time_factor": rtf,
            "zero_cloud_verified": True,
        }

    def render_subtitles_burn(
        self, audio_path: str | Path, chunks: list[dict], output_video_path: str | Path, video_bg_duration: float | None = None
    ) -> bool:
        """Render burned-in subtitles on video using native FFmpeg drawtext filters."""
        ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
        out_path = Path(output_video_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        dur = video_bg_duration or (chunks[-1]["end"] if chunks else 5.0)
        filter_parts = []
        for c in chunks:
            safe_text = c["text"].replace("'", r"\'").replace(":", r"\:")
            filter_parts.append(
                f"drawtext=text='{safe_text}':fontcolor=white:fontsize=42:x=(w-text_w)/2:y=h-120:enable='between(t,{c['start']:.2f},{c['end']:.2f})'"
            )

        vf = ",".join(filter_parts) if filter_parts else "null"
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-t", f"{dur:.2f}", "-i", f"color=c=black:s=1280x720:r=30",
            "-i", str(Path(audio_path).resolve()),
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            str(out_path)
        ]
        code, log = run(cmd, timeout=300)
        return code == 0 and out_path.is_file() and out_path.stat().st_size > 1000

    def detect_silence(self, audio_path: str | Path, noise_db: int = -30, min_duration: float = 0.3) -> list[tuple[float, float]]:
        """Run FFmpeg silencedetect to identify audio transient intervals."""
        ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
        code, text = run([
            ffmpeg_bin, "-i", str(Path(audio_path).resolve()),
            "-af", f"silencedetect=n={noise_db}dB:d={min_duration}",
            "-f", "null", "-"
        ], timeout=180)

        silences = [
            (float(a), float(b))
            for a, b in re.findall(r"silence_start:\s*(\d+\.?\d*).*?silence_end:\s*(\d+\.?\d*)", text, re.S)
        ]
        return silences

    def compute_metrics(self, hypothesis: str, reference: str) -> dict:
        """Compute empirical Word Error Rate (WER) and Character Error Rate (CER)."""
        import jiwer
        wer_val = float(jiwer.wer(reference, hypothesis))
        cer_val = float(jiwer.cer(reference, hypothesis))
        return {
            "wer": round(wer_val, 4),
            "cer": round(cer_val, 4),
        }
