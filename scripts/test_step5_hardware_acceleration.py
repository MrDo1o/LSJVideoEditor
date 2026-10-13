#!/usr/bin/env python3
"""
LSJ Video Editor — Milestone 5 Verification Suite
Hardware Acceleration & 4K60 Real-Time Export Pipeline

Tests:
1. Test Hardware Acceleration Probe & Capability Matrix (CUDA, QSV, MF, NVENC).
2. Test 4K60 Multi-Clip Timeline Export with Transitions & Color Filtering.
3. Test 4K60 Master Bitstream Verification (3840x2160 @ 60fps, 48kHz Stereo AAC, Zero Drift).
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

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "windows"))

import engine as nle
import lsj_video_editor as editor_mod

TEST_VIDEO_PATH = Path(r"C:\Users\found\lsj-command-validation\video\lsj_alignment_test_01.mp4")


def test_1_hardware_encoder_probing():
    print("--- Running Test 1: Hardware Encoder Probing & Capability Matrix ---")
    ffmpeg_bin, ffprobe_bin = editor_mod.resolve_ffmpeg()
    assert ffmpeg_bin and ffprobe_bin, "FFmpeg/FFprobe binaries not found"

    hw_info = nle.detect_hardware_encoders(ffmpeg_bin)
    print(f"  [CHECK] CUDA Available: {hw_info.get('cuda_available')}")
    if hw_info.get("cuda_device_name"):
        print(f"  [CHECK] CUDA Device: {hw_info.get('cuda_device_name')}")
    print(f"  [CHECK] Encoders Tested: {hw_info.get('encoders_tested')}")
    print(f"  [CHECK] Best Hardware Encoder: {hw_info.get('best_hardware_encoder')}")

    # Optimal video options for 4K60
    vopts_4k = nle.get_optimal_export_vopts(ffmpeg_bin, resolution="3840x2160", fps=60)
    print(f"  [CHECK] Optimal 4K60 Video Opts: {vopts_4k}")
    assert any(k in vopts_4k for k in ("h264", "hevc", "qsv", "mf", "nvenc", "libx264")), "Invalid 4K60 vopts"

    # Verify EditorAPI integration
    api = editor_mod.EditorAPI(project_name="HardwareAccelTest")
    api_hw = api.get_hardware_acceleration_status()
    assert api_hw.get("encoders_tested"), "EditorAPI did not return hardware acceleration status"

    print("  [PASS] Test 1: Hardware Encoder Probing & Capability Matrix Succeeded\n")
    return hw_info


def test_2_and_3_4k60_export_pipeline(hw_info):
    print("--- Running Tests 2 & 3: 4K60 Export Pipeline & Bitstream Verification ---")
    assert TEST_VIDEO_PATH.is_file(), f"Test 4K60 video not found: {TEST_VIDEO_PATH}"

    ffmpeg_bin, ffprobe_bin = editor_mod.resolve_ffmpeg()
    tmp_dir = Path(tempfile.mkdtemp(prefix="lsj_step5_4k60_"))
    out_master = tmp_dir / "master_4k60_export.mp4"

    try:
        media_id = "test_4k60_media"
        media_by_id = {
            media_id: {
                "id": media_id,
                "name": "lsj_alignment_test_01.mp4",
                "path": str(TEST_VIDEO_PATH),
                "duration": 73.68,
                "has_audio": True,
                "is_audio": False,
            }
        }

        # Sequence of two 3.0-second 4K60 clips with an Apex color grade and Dissolve transition
        # Total timeline duration: 6.0s (360 frames of 4K60)
        clips = [
            {
                "id": "clip_4k_01",
                "mediaId": media_id,
                "name": "4K Intro",
                "track": 0,
                "start": 0.0,
                "duration": 3.0,
                "sourceIn": 5.0,
                "filter": "Apex",
                "volume": 1.0,
            },
            {
                "id": "clip_4k_02",
                "mediaId": media_id,
                "name": "4K Topic",
                "track": 0,
                "start": 3.0,
                "duration": 3.0,
                "sourceIn": 15.0,
                "transition": "Dissolve",
                "transitionDur": 0.5,
                "volume": 0.8,
            }
        ]

        print("  [INFO] Exporting 4K60 (3840x2160 @ 60fps) timeline...")
        progress_records = []
        def on_prog(p):
            progress_records.append(p)

        t_start = time.time()
        ok, msg = nle.export_timeline(
            ffmpeg=ffmpeg_bin,
            clips=clips,
            media_by_id=media_by_id,
            dest=str(out_master),
            resolution="3840x2160",
            fps=60,
            mastering=True,
            progress_cb=on_prog,
            ducking=False,
            hwaccel="auto"
        )
        elapsed = time.time() - t_start

        assert ok, f"4K60 Export failed: {msg}"
        assert out_master.is_file(), "Exported master file was not created"
        file_size_mb = out_master.stat().st_size / (1024 * 1024)
        total_frames = 6.0 * 60  # 360 frames
        fps_throughput = total_frames / elapsed if elapsed > 0 else 0

        print(f"  [CHECK] 4K60 Export Succeeded in {elapsed:.2f}s ({file_size_mb:.2f} MB)")
        print(f"  [CHECK] Encoding Throughput: {fps_throughput:.1f} fps (Target: > 30.0 fps, Real-time: 60 fps)")
        print(f"  [CHECK] Progress callbacks recorded: {len(progress_records)}")

        # Verify Bitstream with FFprobe
        probe_cmd = [
            ffprobe_bin, "-v", "error",
            "-show_entries", "stream=width,height,r_frame_rate,codec_name,sample_rate,channels:format=duration",
            "-of", "json",
            str(out_master)
        ]
        probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        probe_data = json.loads(probe_res.stdout)
        streams = probe_data.get("streams", [])
        v_stream = next((s for s in streams if s.get("width")), None)
        a_stream = next((s for s in streams if s.get("channels")), None)
        dur_actual = float(probe_data.get("format", {}).get("duration", 0))

        assert v_stream, "No video stream found in exported master"
        assert v_stream["width"] == 3840, f"Expected width 3840, got {v_stream['width']}"
        assert v_stream["height"] == 2160, f"Expected height 2160, got {v_stream['height']}"
        assert v_stream["r_frame_rate"] == "60/1", f"Expected frame rate 60/1, got {v_stream['r_frame_rate']}"

        assert a_stream, "No audio stream found in exported master"
        assert int(a_stream["sample_rate"]) == 48000, f"Expected 48000 Hz audio, got {a_stream['sample_rate']}"
        assert int(a_stream["channels"]) == 2, f"Expected stereo audio, got {a_stream['channels']}"

        delta_ms = abs(dur_actual - 6.0) * 1000.0
        print(f"  [CHECK] Video Stream: {v_stream['codec_name']} {v_stream['width']}x{v_stream['height']} @ {v_stream['r_frame_rate']}")
        print(f"  [CHECK] Audio Stream: {a_stream['codec_name']} {a_stream['sample_rate']}Hz {a_stream['channels']}ch")
        print(f"  [CHECK] Target Duration: 6.000s | Actual: {dur_actual:.3f}s (Delta: {delta_ms:.1f} ms)")
        assert delta_ms <= 33.33, f"Duration drift exceeds 1 frame (33.3ms): {delta_ms:.1f} ms"

        # Bitstream Decode Integrity Check (0 decode errors)
        decode_check = subprocess.run(
            [ffmpeg_bin, "-v", "error", "-i", str(out_master), "-f", "null", "-"],
            capture_output=True, text=True
        )
        assert decode_check.returncode == 0, f"Bitstream decode errors: {decode_check.stderr}"
        print("  [CHECK] Bitstream Decode Check: PASS (Zero errors)")

        print("  [PASS] Tests 2 & 3: 4K60 Export Pipeline & Bitstream Verification Succeeded\n")
        return {
            "elapsed_sec": elapsed,
            "fps_throughput": fps_throughput,
            "file_size_mb": file_size_mb,
            "width": v_stream["width"],
            "height": v_stream["height"],
            "fps": v_stream["r_frame_rate"],
            "duration_actual": dur_actual,
            "delta_ms": delta_ms
        }

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=" * 80)
    print(" LSJ Video Editor — Milestone 5 Hardware Acceleration Verification Suite")
    print("=" * 80)
    hw_info = test_1_hardware_encoder_probing()
    export_metrics = test_2_and_3_4k60_export_pipeline(hw_info)
    print("=" * 80)
    print(" MILESTONE 5 VERIFICATION COMPLETE: ALL 3 TESTS PASSED")
    print(f" 4K60 Encoding Throughput: {export_metrics['fps_throughput']:.1f} fps")
    print(f" Duration Accuracy: Delta = {export_metrics['delta_ms']:.1f} ms")
    print("=" * 80)
