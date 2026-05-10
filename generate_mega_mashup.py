import os
import glob
import subprocess
import json
import random

def get_duration(file_path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Error getting duration for {file_path}: {e}")
        return 0.0

def main():
    directory = "/Volumes/LSJ PROJECTS"
    patterns = ["*.mov", "*.mp4"]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(os.path.join(directory, pattern)))
        
    # Filter out generated files
    valid_files = [f for f in files if "elite_temp" not in f and "_Elite_Cut" not in f and "RenderedVideo" not in f]
    
    all_potential_clips = []
    
    # Filters to use for dynamic angles and watermark cropping
    filters = ["Elite Zoom", "Elite Angle (Right)", "Elite Angle (Left)", "Elite Motion (Pan)"]
    
    for fpath in valid_files:
        dur = get_duration(fpath)
        if dur < 10: # Minimum 10 seconds for a valid source
            continue
            
        # Extract segments based on duration
        if dur > 600: # 10 mins
            num_segments = random.randint(5, 10)
        elif dur > 120: # 2 mins
            num_segments = random.randint(2, 5)
        else:
            num_segments = 1
            
        segment_duration_min = 5
        segment_duration_max = 15
        
        for _ in range(num_segments):
            clip_dur = random.randint(segment_duration_min, segment_duration_max)
            if clip_dur > dur:
                clip_dur = dur - 1
                
            start_time = random.uniform(0, max(0, dur - clip_dur))
            
            all_potential_clips.append({
                "fileURL": fpath,
                "startTime": round(start_time, 2),
                "duration": clip_dur,
                "filter": random.choice(filters)
            })

    # Sample exactly 50 clips if we have enough, otherwise take all
    target_count = 50
    if len(all_potential_clips) > target_count:
        clips = random.sample(all_potential_clips, target_count)
    else:
        clips = all_potential_clips
        print(f"Warning: Only found {len(clips)} potential clips. Target was {target_count}.")

    # Shuffle the clips to create a dynamic mashup arc
    random.shuffle(clips)
    
    timeline = {"clips": clips}
    
    out_json = "/Users/lsjsystemsconsulting/LSJ-Video-Editor-Swift/LSJVideoEditor/mega_arc_timeline.json"
    with open(out_json, "w") as f:
        json.dump(timeline, f, indent=4)
        
    print(f"Generated mega timeline with {len(clips)} clips.")

if __name__ == "__main__":
    main()
