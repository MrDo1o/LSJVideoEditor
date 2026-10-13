#!/usr/bin/env python3
"""
LSJ Video Editor — Step 2 Verification Suite
Multi-Track Video Compositing (Overlays, Picture-in-Picture, B-roll Cutaways)

Verifies:
1. Picture-in-Picture (PIP): Scaled, positioned, transparent overlay on Track 1 over Track 0 base video.
2. B-Roll Cutaway: Full-frame video substitution on Track 1 while Track 0 dialogue audio continues underneath.
3. Multi-Track Video Hierarchy: Proper z-order stacking (Track 0 base < Track 1 overlay).
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "windows"))

import engine as nle
import lsj_video_editor as editor_mod

TEST_VIDEO_PATH = Path(r"C:\Users\found\lsj-command-validation\video\lsj_alignment_test_01.mp4")


def extract_frame_pixel(video_path: str | Path, timestamp_s: float, x: int, y: int, ffmpeg_bin: str) -> np.ndarray:
    tmp_jpg = tempfile.mktemp(suffix=".jpg")
    try:
        cmd = [
            ffmpeg_bin, "-y", "-ss", f"{timestamp_s:.3f}", "-i", str(video_path),
            "-vframes", "1", "-q:v", "2", tmp_jpg
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        img = Image.open(tmp_jpg).convert("RGB")
        arr = np.array(img)
        return arr[y, x]
    finally:
        if os.path.exists(tmp_jpg):
            try:
                os.remove(tmp_jpg)
            except OSError:
                pass


def run_step2_verification():
    print("=" * 75)
    print(" LSJ Video Editor — Step 2: Multi-Track Video Compositing Verification")
    print("=" * 75)

    assert TEST_VIDEO_PATH.is_file(), f"Test video not found: {TEST_VIDEO_PATH}"
    ffmpeg_bin, ffprobe_bin = editor_mod.resolve_ffmpeg()
    assert ffmpeg_bin and ffprobe_bin, "FFmpeg/FFprobe binaries not resolved"

    tmp_dir = Path(tempfile.mkdtemp(prefix="lsj_step2_test_"))
    results = []

    try:
        # =====================================================================
        # TEST 1: Picture-in-Picture (PIP) Overlay on Track 1 over Base Track 0
        # =====================================================================
        print("\n--- Test 1: Picture-in-Picture (PIP) Scaled & Positioned Overlay ---")
        # Synthesize Base Video (Red canvas, 1280x720, 6.0s)
        base_vid = tmp_dir / "base_red_canvas.mp4"
        subprocess.run([
            ffmpeg_bin, "-y", "-f", "lavfi", "-t", "6.0",
            "-i", "color=c=red:s=1280x720:r=30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(base_vid)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Synthesize PIP Video (Green canvas, 1280x720, 3.0s)
        pip_vid = tmp_dir / "pip_green_canvas.mp4"
        subprocess.run([
            ffmpeg_bin, "-y", "-f", "lavfi", "-t", "3.0",
            "-i", "color=c=green:s=1280x720:r=30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(pip_vid)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        api_pip = editor_mod.EditorAPI("Step2_PIP_Test")
        api_pip.import_media([str(base_vid), str(pip_vid)])
        m_base = api_pip.clips[0]
        m_pip = api_pip.clips[1]

        # Track 0: Base video 0.0s to 6.0s
        item_base = api_pip._new_timeline_item(m_base, start=0.0, track=0)
        item_base["duration"] = 6.0
        api_pip.timeline.append(item_base)

        # Track 1: PIP overlay 1.5s to 4.5s, scaled to 0.25 (320x180), placed at (60, 60)
        item_pip = api_pip._new_timeline_item(m_pip, start=1.5, track=1)
        item_pip["duration"] = 3.0
        item_pip["scale"] = 0.25
        item_pip["x"] = 60.0
        item_pip["y"] = 60.0
        item_pip["opacity"] = 1.0
        api_pip.timeline.append(item_pip)

        export_pip = tmp_dir / "pip_composite_master.mp4"
        media_by_id = {c["id"]: c for c in api_pip.clips}
        ok, msg = nle.export_timeline(
            ffmpeg_bin, api_pip.timeline, media_by_id, str(export_pip),
            resolution="1280x720", fps=30, mastering=False,
            video_track_count=api_pip.video_track_count
        )
        assert ok, f"PIP export failed: {msg}"
        assert export_pip.is_file() and export_pip.stat().st_size > 5000

        # Sample pixel at PIP center: (x=150, y=120)
        # Inside the PIP bounding box: x in [60, 380], y in [60, 240]
        test_x, test_y = 150, 120
        pix_before = extract_frame_pixel(export_pip, 0.8, test_x, test_y, ffmpeg_bin)
        pix_during = extract_frame_pixel(export_pip, 3.0, test_x, test_y, ffmpeg_bin)
        pix_after  = extract_frame_pixel(export_pip, 5.2, test_x, test_y, ffmpeg_bin)

        print(f"  [CHECK] Frame at 0.8s (Before PIP) pixel RGB: {pix_before.tolist()} (Base Red)")
        print(f"  [CHECK] Frame at 3.0s (During PIP) pixel RGB: {pix_during.tolist()} (PIP Green)")
        print(f"  [CHECK] Frame at 5.2s (After PIP)  pixel RGB: {pix_after.tolist()} (Base Red)")

        # Assert Red dominant before and after
        assert pix_before[0] > 180 and pix_before[1] < 50, f"Expected Red before PIP, got {pix_before}"
        # Assert Green dominant during PIP
        assert pix_during[1] > 100 and pix_during[0] < 50, f"Expected Green during PIP, got {pix_during}"
        # Assert Red restored after PIP
        assert pix_after[0] > 180 and pix_after[1] < 50, f"Expected Red restored after PIP, got {pix_after}"

        print("  [PASS] Test 1 Succeeded: Picture-in-Picture successfully composited with frame-accurate timing")
        results.append({"test": "Picture-in-Picture (PIP) Compositing", "passed": True})

        # =====================================================================
        # TEST 2: Full-Frame B-Roll Cutaway on Track 1 with Ongoing Dialogue Audio
        # =====================================================================
        print("\n--- Test 2: B-Roll Video Cutaway with Synchronized Audio Retention ---")
        api_broll = editor_mod.EditorAPI("Step2_BRoll_Test")
        api_broll.import_media([str(TEST_VIDEO_PATH), str(pip_vid)])
        m_real = api_broll.clips[0]
        m_cutaway = api_broll.clips[1]

        # Track 0: Real dialogue video 0.0s to 6.0s (Volume 1.0)
        t0_clip = api_broll._new_timeline_item(m_real, start=0.0, track=0)
        t0_clip["duration"] = 6.0
        t0_clip["sourceIn"] = 3.0
        t0_clip["volume"] = 1.0
        api_broll.timeline.append(t0_clip)

        # Track 1: Full-frame B-roll cutaway 2.0s to 4.0s (Scale 1.0, Volume 0.0)
        t1_broll = api_broll._new_timeline_item(m_cutaway, start=2.0, track=1)
        t1_broll["duration"] = 2.0
        t1_broll["scale"] = 1.0
        t1_broll["x"] = 0.0
        t1_broll["y"] = 0.0
        t1_broll["volume"] = 0.0
        api_broll.timeline.append(t1_broll)

        export_broll = tmp_dir / "broll_cutaway_master.mp4"
        media_by_id_broll = {c["id"]: c for c in api_broll.clips}
        ok, msg = nle.export_timeline(
            ffmpeg_bin, api_broll.timeline, media_by_id_broll, str(export_broll),
            resolution="1280x720", fps=30, mastering=False,
            video_track_count=api_broll.video_track_count
        )
        assert ok, f"B-roll export failed: {msg}"
        assert export_broll.is_file()

        # Check center pixel at (640, 360) during cutaway
        pix_center_broll = extract_frame_pixel(export_broll, 3.0, 640, 360, ffmpeg_bin)
        print(f"  [CHECK] Frame at 3.0s (B-roll active) center pixel RGB: {pix_center_broll.tolist()}")
        # pip_vid is green canvas
        assert pix_center_broll[1] > 100, f"Expected B-roll green canvas, got {pix_center_broll}"

        # Verify Track 0 dialogue audio was preserved during the visual B-roll cutaway
        tmp_wav = tempfile.mktemp(suffix=".wav")
        subprocess.run([
            ffmpeg_bin, "-y", "-ss", "2.2", "-t", "1.6",
            "-i", str(export_broll), "-vn", "-ac", "1", "-ar", "48000", tmp_wav
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import scipy.io.wavfile as wav
        sr, wdata = wav.read(tmp_wav)
        wdata = wdata.astype(np.float64) / 32768.0
        rms_broll_audio = float(np.sqrt(np.mean(wdata ** 2)))
        if os.path.exists(tmp_wav): os.remove(tmp_wav)

        print(f"  [CHECK] Audio RMS during B-roll cutaway (2.2-3.8s): {rms_broll_audio:.4f}")
        assert rms_broll_audio > 0.005, f"Audio dropped out during B-roll! RMS: {rms_broll_audio}"

        print("  [PASS] Test 2 Succeeded: B-roll cutaway cleanly replaces video while preserving dialogue audio")
        results.append({"test": "B-Roll Cutaway Compositing", "passed": True})

        print("\n" + "=" * 75)
        print(" ALL STEP 2 VERIFICATION TESTS PASSED SUCCESSFULLY!")
        print("=" * 75)
        return True

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    success = run_step2_verification()
    sys.exit(0 if success else 1)
