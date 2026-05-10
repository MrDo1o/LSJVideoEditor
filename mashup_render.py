import json
import os
import subprocess
import random
from urllib.parse import unquote, urlparse

def mashup_render():
    project_path = '/Users/lsjsystemsconsulting/Documents/LSJVideoProjects/Untitled.lsj'
    output_path = '/Users/lsjsystemsconsulting/Documents/LSJVideoProjects/LSJ_Elite_Rhythm_Mashup.mp4'
    
    with open(project_path, 'r') as f:
        data = json.load(f)
    
    clips = data.get('clips', [])
    if not clips:
        print("No clips found.")
        return

    num_clips = len(clips)
    target_duration = 420 # 7 minutes target
    
    print(f"🔥 Elite Mashup: Sequencing {num_clips} clips into a rhythm-based high-energy cut.")
    
    W, H = 1920, 1080
    inputs = []
    filter_parts = []
    
    # Calculate cuts to build rhythm
    # Start slow (longer clips), end fast (high energy cuts)
    total_segments = num_clips
    
    for i, clip in enumerate(clips):
        raw_url = clip['url']
        parsed_url = urlparse(raw_url)
        local_path = unquote(parsed_url.path)
        
        if not os.path.exists(local_path):
            continue
            
        # Progressive rhythm: clips get shorter as we go (1.0 -> 0.2 factor)
        rhythm_factor = 1.0 - (i / num_clips) * 0.8
        segment_dur = (target_duration / num_clips) * (rhythm_factor * 2) 
        segment_dur = max(0.5, min(segment_dur, clip.get('duration', 5)))
        
        # Pick a random start point that fits the duration
        max_start = max(0, clip.get('duration', 5) - segment_dur)
        start_time = random.uniform(0, max_start)
        
        inputs.extend(["-ss", str(start_time), "-t", str(segment_dur), "-i", local_path])
        
        # ELITE AI PROFILE + Rhythm Scaling
        vf = (
            f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,"
            f"nlmeans=s=1.0:p=5:r=3," 
            f"unsharp=3:3:0.6:3:3:0.0," # Slightly more sharpening for high energy
            f"setsar=1[v{i}];"
            f"[{i}:a]anull[a{i}]"
        )
        filter_parts.append(vf)
    
    concat_filter = "".join([f"[v{i}][a{i}]" for i in range(len(filter_parts))])
    concat_filter += f"concat=n={len(filter_parts)}:v=1:a=1[outv][outa]"
    
    full_filter = "".join(filter_parts) + concat_filter
    
    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", full_filter,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "h264_videotoolbox", "-b:v", "9000k", # Higher bitrate for fast motion
        "-profile:v", "high",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest",
        output_path
    ]
    
    print(f"🚀 MASHUP RENDER STARTED (Target: ~7 mins, High Energy Finale)...")
    with open("mashup_log.txt", "w") as log:
        subprocess.Popen(cmd, stdout=log, stderr=log)
    
    print(f"✅ Rhythm Mashup active: {output_path}")

if __name__ == "__main__":
    mashup_render()
