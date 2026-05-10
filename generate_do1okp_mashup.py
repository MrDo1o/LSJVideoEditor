import os
import json
import random
import subprocess

def main():
    fpath = "/Volumes/LSJ PROJECTS/Do1oKP.mov"
    dur = 2185.0
    
    clips = []
    filters = ["Elite Zoom", "Elite Angle (Right)", "Elite Angle (Left)", "Elite Motion (Pan)"]
    
    # We will take 8 segments, 3 to 10 minutes each
    num_segments = 8
    segment_duration_min = 180
    segment_duration_max = 600
    
    for _ in range(num_segments):
        clip_dur = random.randint(segment_duration_min, segment_duration_max)
        if clip_dur > dur:
            clip_dur = dur - 1
            
        start_time = random.uniform(0, max(0, dur - clip_dur))
        
        clips.append({
            "fileURL": fpath,
            "startTime": round(start_time, 2),
            "duration": clip_dur,
            "filter": random.choice(filters)
        })

    # Shuffle the clips to create a dynamic mashup arc
    random.shuffle(clips)
    
    timeline = {"clips": clips}
    
    out_json = "/Users/lsjsystemsconsulting/LSJ-Video-Editor-Swift/LSJVideoEditor/do1okp_arc_timeline.json"
    with open(out_json, "w") as f:
        json.dump(timeline, f, indent=4)
        
    print(f"Generated do1okp timeline with {len(clips)} clips.")

if __name__ == "__main__":
    main()
