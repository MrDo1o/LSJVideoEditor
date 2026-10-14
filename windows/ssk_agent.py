#!/usr/bin/env python3
"""
Sovereign Speech Kit (SSK) — Autonomous NLE Director Agent
Powered by Google Antigravity SDK (`google.antigravity`)

This agent runs 100% locally on your machine, interfacing directly with
the LSJ Video Editor timeline engine and FFmpeg hardware acceleration.
It operates without cloud censorship, telemetry leakage, or third-party filters.
"""

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

# Add windows folder to path to import LSJ Video Editor engine
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "windows"))

import engine as nle
import lsj_video_editor as editor_mod
from google.antigravity import Agent, LocalOpenAIAgentConfig

# Global instance of the EditorAPI for the agent tools
_api_instance = None


def get_api() -> editor_mod.EditorAPI:
    global _api_instance
    if _api_instance is None:
        _api_instance = editor_mod.EditorAPI()
    return _api_instance


# =============================================================================
# Sovereign NLE Agent Tools (Decorated with docstrings for Antigravity SDK)
# =============================================================================

def import_media(file_paths: list[str]) -> str:
    """Imports one or more video or audio files into the media bin.

    Args:
        file_paths: List of absolute file paths to video or audio clips.
    """
    api = get_api()
    valid_paths = []
    errors = []
    for fp in file_paths:
        p = Path(fp.strip('"\''))
        if not p.is_file():
            errors.append(f"Not found: {fp}")
        else:
            valid_paths.append(str(p.resolve()))

    if valid_paths:
        api.import_media(paths=valid_paths)

    added = [f"{c.get('name', 'Clip')} ({c.get('duration', 0.0):.1f}s)" for c in api.clips]
    res = f"Imported {len(added)} clips:\n  " + "\n  ".join(added)
    if errors:
        res += "\nErrors:\n  " + "\n  ".join(errors)
    return res


def build_highlight_mashup(target_duration_sec: float = 300.0) -> str:
    """Assembles an autonomous, high-energy highlight mashup across all imported clips.

    Slices rhythmic cutaways across all loaded media, aligns them dynamically to the target
    duration, and applies smooth transitions between adjacent scenes.

    Args:
        target_duration_sec: Desired total duration of the highlight reel in seconds (default: 300.0 for 5 minutes).
    """
    api = get_api()
    if not api.clips:
        return "Error: No clips in media bin. Please import media first using import_media."

    api.mashup(seconds=float(target_duration_sec))
    total_dur = max((c["start"] + c["duration"] for c in api.timeline if c.get("track", 0) == 0), default=0.0)
    return f"Successfully generated highlight mashup! Timeline has {len(api.timeline)} cuts spanning {total_dur:.1f} seconds."


def action_pulse() -> str:
    """Executes high-energy action-pulse cutting using local scene detection and beat transients.

    Extracts rapid (<1.6s) rhythmic cuts from the selected or first video clip, applies punch-in
    scale zooms, and appends them to the timeline for maximum intensity.
    """
    api = get_api()
    if not api.clips:
        return "Error: No clips in media bin."
    if not api.selected_clip_id and api.clips:
        api.selected_clip_id = api.clips[0]["id"]

    media = api.clip_by_id(api.selected_clip_id)
    name = media.get("name", "Clip") if media else "Clip"
    api.action_pulse()
    total_dur = max((c["start"] + c["duration"] for c in api.timeline if c.get("track", 0) == 0), default=0.0)
    return f"Action pulse complete for '{name}'! Timeline now contains {len(api.timeline)} cuts spanning {total_dur:.1f}s."


def beat_sync() -> str:
    """Analyzes audio transients and cuts video in exact sync with rhythmic beats."""
    api = get_api()
    if not api.clips:
        return "Error: No clips in media bin."
    if not api.selected_clip_id and api.clips:
        api.selected_clip_id = api.clips[0]["id"]

    api.beat_sync()
    total_dur = max((c["start"] + c["duration"] for c in api.timeline if c.get("track", 0) == 0), default=0.0)
    return f"Beat sync complete! Timeline has {len(api.timeline)} cuts spanning {total_dur:.1f}s."


def remove_silence(threshold_db: float = -30.0, min_silence_dur: float = 0.4) -> str:
    """Detects and removes acoustic silence and dead air with sample-accurate ripple closure.

    Keeps video tracks, companion detached audio, PIP overlays, and chapter markers in 0.00ms lockstep.

    Args:
        threshold_db: Decibel threshold below which audio is considered silence (default: -30.0 dB).
        min_silence_dur: Minimum duration of pause in seconds to excise (default: 0.4s).
    """
    api = get_api()
    track0_clips = [c for c in api.timeline if c.get("track", 0) == 0]
    if not track0_clips:
        return "Error: No video clips on timeline."

    api.selected_timeline_ids = [c["id"] for c in track0_clips]
    ok = api.remove_silence(threshold_db=threshold_db, min_silence_dur=min_silence_dur)
    if ok:
        total_dur = max((c["start"] + c["duration"] for c in api.timeline if c.get("track", 0) == 0), default=0.0)
        return f"Smart Silence Removal succeeded: {api.ai_status}. Compacted timeline duration: {total_dur:.1f}s."
    return "Smart Silence Removal failed or no silence detected."


def get_timeline_status() -> str:
    """Returns the current state of the timeline, including clip count, tracks, duration, and markers."""
    api = get_api()
    if not api.timeline:
        return f"Timeline is empty. Media bin contains {len(api.clips)} clips."

    total_dur = max((c["start"] + c["duration"] for c in api.timeline if c.get("track", 0) == 0), default=0.0)
    lines = [
        f"Timeline Summary:",
        f"  Total Duration: {total_dur:.2f}s ({total_dur / 60.0:.2f} minutes)",
        f"  Total Clips: {len(api.timeline)}",
        f"  Media Bin Assets: {len(api.clips)}",
        f"  Chapter Markers: {len(getattr(api, 'markers', []))}"
    ]
    for i, c in enumerate(api.timeline[:10]):
        lines.append(f"    [{i+1}] Track {c.get('track', 0)}: {c.get('name', 'Clip')} (start={c.get('start', 0):.2f}s, dur={c.get('duration', 0):.2f}s)")
    if len(api.timeline) > 10:
        lines.append(f"    ... and {len(api.timeline) - 10} more clips")
    return "\n".join(lines)


def export_master(dest_path: str = "", resolution: str = "1920x1080", fps: int = 60) -> str:
    """Renders the active timeline into a finished video using local GPU hardware acceleration.

    Args:
        dest_path: Destination file path (.mp4 or .mov). If empty, exports to user's Videos folder.
        resolution: Output resolution, e.g. '1920x1080' or '3840x2160' (default: '1920x1080').
        fps: Output frame rate (default: 60).
    """
    api = get_api()
    if not api.timeline:
        return "Error: Timeline is empty. Nothing to export."

    if not dest_path:
        dest_path = str(Path.home() / "Videos" / f"SSK_Highlight_Reel_{int(time.time())}.mp4")
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    media_by_id = {c["id"]: c for c in api.clips}
    ffmpeg_bin, _ = editor_mod.resolve_ffmpeg()

    t_start = time.time()
    ok, log = nle.export_timeline(
        ffmpeg=ffmpeg_bin,
        clips=api.timeline,
        media_by_id=media_by_id,
        dest=str(dest),
        resolution=resolution,
        fps=int(fps),
        mastering=True,
        ducking=api.audio_ducking,
        hwaccel="auto"
    )
    elapsed = time.time() - t_start
    if ok and dest.is_file():
        size_mb = dest.stat().st_size / (1024 * 1024)
        return f"Export successful!\n  Destination: {dest}\n  File Size: {size_mb:.2f} MB\n  Render Time: {elapsed:.1f}s"
    return f"Export failed: {log}"


def clear_timeline() -> str:
    """Clears all clips from the current timeline."""
    api = get_api()
    api.timeline = []
    api.markers = []
    return "Timeline cleared."


SSK_TOOLS = [
    import_media,
    build_highlight_mashup,
    action_pulse,
    beat_sync,
    remove_silence,
    get_timeline_status,
    export_master,
    clear_timeline
]


# =============================================================================
# Agent Runner & Deterministic Execution Dispatcher
# =============================================================================

SSK_SYSTEM_INSTRUCTIONS = """You are SSK (Sovereign Speech Kit), the autonomous AI Video Director for LSJ Video Editor.
You operate strictly locally on the user's personal hardware with zero cloud censorship, zero external scanning, and zero telemetry.
You have direct access to tools to import media, slice high-energy highlight mashups, execute beat-synced cuts, remove silence, and export finished master videos.

Always fulfill the user's creative video editing requests directly by calling the appropriate tools.
When asked to make a highlight reel, import the clips, call build_highlight_mashup or action_pulse, and report the results.
Keep your text responses concise and focused on the timeline state."""


async def run_ssk_agent(prompt: str, files: list[str] | None = None, output: str | None = None):
    api = get_api()

    # Pre-import files if supplied via CLI
    if files:
        print(f"[*] Pre-importing {len(files)} files into SSK media bin...")
        import_res = import_media(files)
        print(import_res)

    # 1. Check for Dokk/Kweenesha local model or OpenAI-compatible server
    base_url = os.environ.get("LSJ_LLM_URL") or os.environ.get("LLAMA_URL") or "http://127.0.0.1:8081/v1"
    model_name = os.environ.get("KE_BRIDGE_MODEL") or os.environ.get("SSK_MODEL") or "ssk-open-disambiguation-v1"
    local_model_path = Path(r"C:\Users\found\models\Kweenesha-Base-v1.gguf")

    print(f"\n[SSK] Initializing Sovereign Director Agent via Google Antigravity SDK...")
    print(f"      Model Lineage: {model_name} (Protocol IOPQ-08 Locked Baseline)")
    print(f"      Local Model Checkpoint: {local_model_path.name if local_model_path.is_file() else 'Online'}")
    print(f"      Backend Target: {base_url}")

    server_live = False
    try:
        import urllib.request
        req = urllib.request.Request(base_url.rstrip("/v1") + "/api/tags" if "11434" in base_url else base_url, headers={"User-Agent": "SSK"})
        with urllib.request.urlopen(req, timeout=1.5):
            server_live = True
    except Exception:
        server_live = False

    if server_live:
        print(f"[SSK] Connected to local AI model server at {base_url}.")
        config = LocalOpenAIAgentConfig(
            model=model_name,
            base_url=base_url,
            system_instructions=SSK_SYSTEM_INSTRUCTIONS,
            tools=SSK_TOOLS,
        ).lightweight()

        async with Agent(config=config) as agent:
            print(f"\nUser > {prompt}")
            print("SSK > ", end="", flush=True)
            response = await agent.chat(prompt)
            async for chunk in response:
                print(chunk, end="", flush=True)
            print()
    else:
        print(f"[SSK] Note: Local server {base_url} is not actively responding.")
        print(f"[SSK] Activating Sovereign Heuristic Pipeline (Zero-Latency Deterministic Director)...")
        # Deterministic autonomous execution
        p_lower = prompt.lower()
        if "mashup" in p_lower or "highlight" in p_lower or "reel" in p_lower:
            target = 300.0
            import re
            m = re.search(r"(\d+)\s*(?:min|minute)", p_lower)
            if m:
                target = float(m.group(1)) * 60.0
            print(f"\n[SSK Tool Call] build_highlight_mashup(target_duration_sec={target})")
            res = build_highlight_mashup(target_duration_sec=target)
            print(f"  -> {res}")

        if "pulse" in p_lower or "action" in p_lower:
            print(f"\n[SSK Tool Call] action_pulse()")
            res = action_pulse()
            print(f"  -> {res}")

        if "silence" in p_lower:
            print(f"\n[SSK Tool Call] remove_silence()")
            res = remove_silence()
            print(f"  -> {res}")

        if output or "export" in p_lower or "render" in p_lower:
            out_file = output or str(Path.home() / "Videos" / f"SSK_Highlight_Reel_{int(time.time())}.mp4")
            print(f"\n[SSK Tool Call] export_master(dest_path='{out_file}')")
            res = export_master(dest_path=out_file)
            print(f"  -> {res}")

        print("\n[SSK Timeline State]")
        print(get_timeline_status())


async def interactive_session(initial_files=None):
    print("=" * 76)
    print("  SOVEREIGN SPEECH KIT (SSK) — Autonomous NLE Director")
    print("  Engine: Local GPU (Intel QSV / CUDA) | Zero Cloud Censorship")
    print("=" * 76)

    api = get_api()
    candidates = list(initial_files) if initial_files else []
    for check_path in [Path("my_clips.txt"), REPO_ROOT / "my_clips.txt", Path.cwd() / "my_clips.txt"]:
        if check_path.is_file():
            with open(check_path, "r", encoding="utf-8") as f:
                for line in f:
                    l = line.strip().strip('"\'')
                    if l and not l.startswith("#"):
                        candidates.append(l)
            print(f"[*] Auto-detected clip manifest: {check_path.name} ({len(candidates)} clips)")
            break

    if candidates and not api.clips:
        print(import_media(candidates))

    print(f"\n[SSK Ready] Media bin contains {len(api.clips)} clips. Active timeline: {len(api.timeline)} cuts.")
    print("\nCommands you can type:")
    print("  - 'mashup 5 min' or 'highlight reel' -> Assembles 5-minute dynamic montage")
    print("  - 'pulse'                            -> High-energy rapid action cuts")
    print("  - 'beat'                             -> Musical beat-synced cuts")
    print("  - 'silence'                          -> Excises dead air with 0.00ms ripple sync")
    print("  - 'export'                           -> Renders master to Videos/ folder via GPU")
    print("  - 'status'                           -> Shows timeline breakdown and duration")
    print("  - 'clear'                            -> Empties timeline for fresh cut")
    print("  - 'exit'                             -> Quits session\n")

    while True:
        try:
            user_prompt = input("SSK > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[SSK] Session terminated. Goodbye!")
            break

        if not user_prompt:
            continue
        if user_prompt.lower() in ("exit", "quit", "q"):
            print("[SSK] Session terminated. Goodbye!")
            break

        await run_ssk_agent(prompt=user_prompt)


def main():
    parser = argparse.ArgumentParser(description="SSK Sovereign NLE Director Agent")
    parser.add_argument("--prompt", type=str, default=None, help="Instruction for SSK agent (if omitted, starts interactive chat)")
    parser.add_argument("--files", nargs="*", default=None, help="Paths of media files to import")
    parser.add_argument("--filelist", type=str, default=None, help="Text file containing paths of media files to import (one per line)")
    parser.add_argument("--output", type=str, default=None, help="Destination export path")
    args = parser.parse_args()

    all_files = list(args.files) if args.files else []
    if args.filelist:
        fl_path = Path(args.filelist)
        if fl_path.is_file():
            with open(fl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip().strip('"\'')
                    if line and not line.startswith("#"):
                        all_files.append(line)

    if args.prompt:
        asyncio.run(run_ssk_agent(prompt=args.prompt, files=all_files if all_files else None, output=args.output))
    else:
        asyncio.run(interactive_session(initial_files=all_files if all_files else None))


if __name__ == "__main__":
    main()
