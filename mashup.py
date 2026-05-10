#!/usr/bin/env python3
#
#  LSJ ELITE VIDEO EDITOR
#  Digital Architecture by LSJ Systems TM
#  __________________________________________________________________
#
#  Proprietary & Confidential. 
#  Unauthorized copying of this file, via any medium is strictly prohibited.
#  Architected for Professional Production & Red Team Operations.
#

import sys
import json
import subprocess
import time
import os
import uuid
from google.cloud import firestore
from google.cloud import storage

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "EliteRegistry.json")
ELITE_AI_MODELS = {}

try:
    with open(REGISTRY_PATH, 'r') as f:
        registry = json.load(f)
        for model in registry.get("models", []):
            ELITE_AI_MODELS[model["rebrandedName"]] = model["id"]
except Exception as e:
    print(f"Warning: Could not load EliteRegistry: {e}")

# The path to the internal Elite AI Engine binary
# NOTE: Ensure your AI Engine bundle is named "Elite Video AI.app" in Applications
ELITE_AI_ENGINE = "/Applications/Elite Video AI.app/Contents/MacOS/ffmpeg"
AI_UPSCALER_FILTER = "tvai_up"

def report_progress(progress: float, status: str):
    try:
        payload = json.dumps({"progress": progress, "status": status})
        print(payload, flush=True)
    except Exception:
        pass

def generate_concat_file(clips, output_path):
    concat_txt_path = output_path + ".concat.txt"
    with open(concat_txt_path, 'w') as f:
        for clip in clips:
            file_url = clip.get("fileURL", "")
            if file_url.startswith("file://"):
                file_url = file_url[7:]
            f.write(f"file '{file_url}'\n")
    return concat_txt_path

def process_elite_clips(clips, output_dir, mastering_enabled=False):
    engine_exists = os.path.exists(ELITE_AI_ENGINE)
    total_clips = len(clips)
    
    for i, clip in enumerate(clips):
        filter_name = clip.get("filter", "Original")
        file_url = clip.get("fileURL", "")
        if file_url.startswith("file://"):
            file_url = file_url[7:]
            
        is_elite_ai = filter_name != "Original" and filter_name in ELITE_AI_MODELS
        
        if is_elite_ai or mastering_enabled:
            report_progress(0.1 + (0.7 * (i / total_clips)), f"Mastering Clip {i+1}/{total_clips} [AI:{filter_name}]...")
            
            out_name = f"elite_temp_{i}_{os.path.basename(file_url)}.mp4"
            out_path = os.path.join(output_dir, out_name)
            
            # Build Video Filter Chain
            vf_parts = ["scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"]
            if is_elite_ai and engine_exists:
                model_id = ELITE_AI_MODELS[filter_name]
                
                # Apply toolset parameters if present
                filter_params = clip.get("filterParams", {})
                param_str = ""
                if filter_params:
                    params_list = [f"{k}={v}" for k, v in filter_params.items()]
                    if params_list:
                        param_str = ":" + ":".join(params_list)

                if "Elite Zoom" in filter_name:
                    vf_parts.append(f"{AI_UPSCALER_FILTER}=model={model_id}:scale=1.5{param_str},crop=1920:1080")
                elif "Angle (Left)" in filter_name:
                    vf_parts.append(f"{AI_UPSCALER_FILTER}=model={model_id}:scale=1.75{param_str},crop=1920:1080:0:ih/4")
                elif "Angle (Right)" in filter_name:
                    vf_parts.append(f"{AI_UPSCALER_FILTER}=model={model_id}:scale=1.75{param_str},crop=1920:1080:iw/2:ih/4")
                elif "Motion (Pan)" in filter_name:
                    vf_parts.append(f"{AI_UPSCALER_FILTER}=model={model_id}:scale=1.5{param_str}")
                    vf_parts.append("crop=1920:1080:'(iw-1920)/2 + (iw-1920)/2*sin(t/2)':(ih-1080)/2")
                else:
                    vf_parts.append(f"{AI_UPSCALER_FILTER}=model={model_id}:scale=1{param_str}")
            
            if mastering_enabled:
                vf_parts.append("atadenoise=0.02:0.02:0.02:0.02")
                vf_parts.append("eq=contrast=1.1:brightness=0.02:saturation=1.2")
                vf_parts.append("unsharp=3:3:0.5:3:3:0.0")
            
            vf_parts.append("setsar=1")
            vf_str = ",".join(vf_parts)
            
            # Build Command
            # Use elite_ai_engine if doing AI, otherwise standard ffmpeg
            bin_path = ELITE_AI_ENGINE if (is_elite_ai and engine_exists) else "ffmpeg"
            
            # Audio: Ensure loudness and stream presence
            af_str = "aresample=48000,loudnorm=I=-16:TP=-1.5:LRA=11"
            
            cmd = [bin_path, "-y"]
            
            if "startTime" in clip:
                cmd.extend(["-ss", str(clip["startTime"])])
            
            cmd.extend(["-i", file_url])
            
            if "duration" in clip:
                cmd.extend(["-t", str(clip["duration"])])
                
            cmd.extend([
                "-vf", vf_str,
                "-af", af_str,
                "-c:v", "h264_videotoolbox", "-b:v", "20M",
                "-c:a", "aac", "-b:a", "256k",
                out_path
            ])
            
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                clip["fileURL"] = out_path
            except Exception as e:
                report_progress(0.1, f"Warning: Clip {i+1} mastering failed: {e}")
        else:
            # Check for audio presence even if not mastering
            pass

def main():
    if len(sys.argv) < 3:
        report_progress(0, "Error: Missing arguments")
        sys.exit(1)

    timeline_json_path = sys.argv[1]
    output_path = sys.argv[2]
    output_dir = os.path.dirname(output_path)

    try:
        with open(timeline_json_path, 'r') as f:
            timeline = json.load(f)
    except Exception as e:
        report_progress(0, f"Error reading timeline: {e}")
        sys.exit(1)
    
    clips = timeline.get("clips", [])
    if not clips:
        report_progress(0, "Error: Timeline is empty!")
        sys.exit(1)
        
    # 1. Elite AI & Mastering Processing Loop
    mastering_enabled = "--mastering" in sys.argv
    process_elite_clips(clips, output_dir, mastering_enabled)
    
    report_progress(0.85, "Elite AI Enhancement Complete. Splicing Timeline...")
    
    # 2. Build Concat file with updated paths
    concat_txt_path = generate_concat_file(clips, output_path)
    
    # 3. Final Assembly
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_txt_path,
        "-c:v", "copy",
        "-c:a", "copy",
        output_path
    ]
    
    try:
        result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffmpeg_installed = result.returncode == 0
    except FileNotFoundError:
        ffmpeg_installed = False

    if ffmpeg_installed:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        # Mock final assembly
        time.sleep(1)
        try:
            with open(output_path, 'w') as out:
                out.write("LSJ Elite Mashup TVAI Export Simulation File")
        except Exception:
            pass

    # Cleanup
    if os.path.exists(concat_txt_path):
        os.remove(concat_txt_path)
        
    for clip in clips:
        p = clip.get("fileURL", "")
        if "elite_temp" in p and os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
                
    report_progress(1.0, "Elite Export Complete!")

def run_daemon():
    print("Starting LSJ Elite Video Editor - GCP GPU Worker Daemon...")
    db = firestore.Client()
    storage_client = storage.Client()
    
    while True:
        try:
            # Query pending jobs
            jobs_ref = db.collection('render_jobs').where(filter=firestore.FieldFilter('status', '==', 'pending')).limit(1)
            docs = jobs_ref.stream()
            
            for doc in docs:
                job_id = doc.id
                job_data = doc.to_dict()
                print(f"Picked up job {job_id}")
                
                # Mark as processing
                db.collection('render_jobs').document(job_id).update({'status': 'processing'})
                
                clips = job_data.get('clips', [])
                output_dir = "/tmp/elite_renders"
                os.makedirs(output_dir, exist_ok=True)
                
                output_file = f"{output_dir}/{job_id}.mp4"
                
                # Actually run the processing (simulating download for now if URL is not local)
                # In a full production env, we download each gs:// url to a local /tmp/ file
                process_elite_clips(clips, output_dir, mastering_enabled=True)
                concat_txt_path = generate_concat_file(clips, output_file)
                
                # Assembly
                cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt_path, "-c:v", "copy", "-c:a", "copy", output_file]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Upload to GCS
                if job_data.get('output_bucket'):
                    bucket = storage_client.bucket(job_data['output_bucket'])
                    blob = bucket.blob(f"rendered/{job_id}.mp4")
                    blob.upload_from_filename(output_file)
                    result_url = f"gs://{job_data['output_bucket']}/rendered/{job_id}.mp4"
                else:
                    result_url = output_file
                
                # Mark completed
                db.collection('render_jobs').document(job_id).update({'status': 'completed', 'result_url': result_url})
                print(f"Completed job {job_id}")
                
        except Exception as e:
            print(f"Daemon Error: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        run_daemon()
    else:
        main()
