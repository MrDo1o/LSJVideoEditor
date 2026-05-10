import os
import subprocess
import json
import random

SOURCE_DIR = "/Volumes/LSJ PROJECTS/Bae"
OUT_JSON = "/Users/lsjsystemsconsulting/LSJ-Video-Editor-Swift/LSJVideoEditor/bae_arc_timeline.json"

# Known source files (from earlier ls, in natural order)
# Excludes elite_temp_* processed artifacts
SOURCE_FILES = [
    "Bae - 1.MP4",
    "Bae - 2.MP4",
    "Bae - 3.MP4",
    "Bae - 4.MP4",
    "Bae - 5.MP4",
    "Bae - 6.MP4",
    "Bae - 7.MP4",
    "Bae - 8.MP4",
    "Bae - 9.MP4",
    "Bae - 10.MP4",
    "Bae - 11.MP4",
    "Bae - 12.MP4",
    "Bae - 13.MP4",
    "Bae - 14.MP4",
    "IMG_3841.MP4",
]

# Durations from ffprobe (captured earlier session)
# Will be overridden if ffprobe access works
KNOWN_DURATIONS = {
    "Bae - 1.MP4": 15.0,
    "Bae - 2.MP4": 15.0,
    "Bae - 3.MP4": 85.0,
    "Bae - 4.MP4": 85.0,
    "Bae - 5.MP4": 39.0,
    "Bae - 6.MP4": 39.0,
    "Bae - 7.MP4": 37.0,
    "Bae - 8.MP4": 37.0,
    "Bae - 9.MP4": 34.0,
    "Bae - 10.MP4": 34.0,
    "Bae - 11.MP4": 49.0,
    "Bae - 12.MP4": 49.0,
    "Bae - 13.MP4": 154.0,
    "Bae - 14.MP4": 124.0,
    "IMG_3841.MP4": 157.0,
}

# Filters that crop edges (kills watermarks) while keeping content dynamic
FILTERS = [
    "Elite Zoom",
    "Elite Angle (Right)",
    "Elite Angle (Left)",
    "Elite Motion (Pan)",
]


def get_duration(file_path: str) -> float:
    """Get video duration via ffprobe, fall back to known durations."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        dur = float(result.stdout.strip())
        if dur > 0:
            return dur
    except Exception:
        pass

    # Fallback to known durations
    basename = os.path.basename(file_path)
    return KNOWN_DURATIONS.get(basename, 30.0)


def main():
    print(f"[*] Building Bae mashup timeline from {len(SOURCE_FILES)} source clips")

    clips = []
    total_duration = 0.0

    for filename in SOURCE_FILES:
        fpath = os.path.join(SOURCE_DIR, filename)
        dur = get_duration(fpath)

        if dur < 2:
            print(f"  [skip] {filename} — too short ({dur:.1f}s)")
            continue

        chosen_filter = random.choice(FILTERS)
        clip = {
            "fileURL": fpath,
            "startTime": 0,
            "duration": round(dur, 2),
            "filter": chosen_filter,
        }
        clips.append(clip)
        total_duration += dur
        print(f"  [+] {filename:30s}  {dur:>7.1f}s  filter={chosen_filter}")

    # Write JSON timeline
    timeline = {"clips": clips}
    with open(OUT_JSON, "w") as f:
        json.dump(timeline, f, indent=4)

    minutes = total_duration / 60
    print(f"\n[✓] Timeline written → {OUT_JSON}")
    print(f"    {len(clips)} clips | {total_duration:.1f}s ({minutes:.1f} min) total")
    print(f"\n[!] Open LSJVideoEditor Xcode project and load this timeline to render.")


if __name__ == "__main__":
    main()
