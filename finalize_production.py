#!/usr/bin/env python3
import os
import subprocess
import sys

def run_command(cmd, description):
    print(f"🚀 {description}...")
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ {description} Complete.\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}: {e}")
        sys.exit(1)

def main():
    base_dir = "/Users/lsjsystemsconsulting/LSJ-Video-Editor-Swift/LSJVideoEditor"
    output_dir = "/Volumes/LSJ PROJECTS/MASTERED_EXPORTS"
    os.makedirs(output_dir, exist_ok=True)

    # 1. Generate Timelines
    run_command(["python3", os.path.join(base_dir, "generate_mega_mashup.py")], "Generating Mega Mashup Timeline (50 Clips)")
    run_command(["python3", os.path.join(base_dir, "generate_bae_mashup.py")], "Generating Bae Narrative Arc Timeline")
    run_command(["python3", os.path.join(base_dir, "generate_do1okp_mashup.py")], "Generating Do1oKP Narrative Arc Timeline")

    # 2. Render & Master
    jobs = [
        ("mega_arc_timeline.json", "Mega_Mashup_50_Clip_Elite.mp4"),
        ("bae_arc_timeline.json", "Bae_Narrative_Arc_Elite.mp4"),
        ("do1okp_arc_timeline.json", "Do1oKP_Narrative_Arc_Elite.mp4")
    ]

    for timeline, output_name in jobs:
        timeline_path = os.path.join(base_dir, timeline)
        output_path = os.path.join(output_dir, output_name)
        
        # Call mashup.py with --mastering for GPU accelerated mastering
        run_command([
            "python3", 
            os.path.join(base_dir, "mashup.py"), 
            timeline_path, 
            output_path, 
            "--mastering"
        ], f"Mastering & Rendering {output_name}")

    print("🏁 ALL PRODUCTION JOBS COMPLETE. Exports located in: " + output_dir)

if __name__ == "__main__":
    main()
