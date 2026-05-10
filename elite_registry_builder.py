import json
import glob
import os
import re

MODELS_DIR = "/Applications/Topaz Video AI.app/Contents/Resources/models"
OUTPUT_FILE = "/Users/lsjsystemsconsulting/LSJ-Video-Editor-Swift/LSJVideoEditor/EliteRegistry.json"

EXISTING_MAP = {
    "prob-4": "Apex",
    "iris-3": "Prism",
    "rhea-1": "Lumina",
    "rxl-1": "Titan",
    "ghq-5": "Terra",
    "gcg-5": "Render",
    "nyx-3": "Obsidian",
    "nxf-1": "Shadow",
    "amq-13": "Vector",
    "aaa-10": "Vector Auto",
    "ahq-12": "Vector HQ",
    "dtv-4": "Stellar",
    "ddv-3": "Echo",
    "dtd-4": "Grit",
    "dtvs-2": "Halo",
    "chr-2": "Flux",
    "chf-3": "Pulsar",
    "apo-8": "Helios",
    "apf-2": "Aurora",
    "aion-1": "Aeon",
    "thm-2": "Zenith",
    "thd-3": "Focus",
    "thf-4": "Fidelity",
    "hyp-1": "Solstice",
    "ash-1": "Vanguard",
    "ref-2": "Stabilizer"
}

def clean_name(name):
    name = re.sub(r'[^a-zA-Z0-9\s-]', '', name)
    return name.strip()

def build_registry():
    registry = {
        "models": [],
        "video_encoders": [],
        "audio_codecs": []
    }

    # 1. Parse Models
    model_files = glob.glob(os.path.join(MODELS_DIR, "*.json"))
    ignore_files = ["benchmarks.json", "model-recommendation-rules.json", "video-encoders.json", "audio-codecs.json"]
    
    for fpath in model_files:
        fname = os.path.basename(fpath)
        if fname in ignore_files:
            continue
            
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
                
            short_name = data.get("shortName", "")
            version = data.get("version", "")
            model_id = f"{short_name}-{version}"
            
            gui_info = data.get("gui", {})
            original_name = gui_info.get("name", fname.replace(".json", ""))
            
            # Rebrand Name
            rebranded_name = EXISTING_MAP.get(model_id)
            if not rebranded_name:
                clean_orig = clean_name(original_name)
                rebranded_name = f"Elite {clean_orig} (v{version})"
                
            extra_params = data.get("extraParameters", [])
            # Determine Category
            category = "Other"
            if model_id in ["prob-4", "iris-3", "rhea-1", "rxl-1", "ghq-5", "gcg-5", "nyx-3", "nxf-1"]:
                category = "Enhance"
            elif model_id in ["amq-13", "aaa-10", "ahq-12"]:
                category = "Vector"
            elif model_id in ["dtv-4", "ddv-3", "dtd-4", "dtvs-2"]:
                category = "Deinterlace"
            elif model_id in ["chr-2", "chf-3", "apo-8", "apf-2", "aion-1"]:
                category = "Motion"
            elif model_id in ["thm-2", "thd-3", "thf-4", "hyp-1", "ash-1", "ref-2"]:
                category = "Special"
            elif "Elite Zoom" in original_name or "Angle" in original_name or "Pan" in original_name:
                category = "Helpers"
            else:
                category = "Legacy"
                
            registry["models"].append({
                "id": model_id,
                "rebrandedName": rebranded_name,
                "originalName": original_name,
                "shortName": short_name,
                "version": version,
                "category": category,
                "parameters": extra_params
            })
        except Exception as e:
            print(f"Error parsing {fname}: {e}")
            
    # Sort models by rebranded name
    registry["models"].sort(key=lambda x: x["rebrandedName"])

    # 2. Parse Video Encoders
    try:
        with open(os.path.join(MODELS_DIR, "video-encoders.json"), 'r') as f:
            encoders = json.load(f)
            for enc in encoders:
                enc_id = enc.get("id", "")
                enc_name = enc.get("encoder", "Unknown")
                enc_profile = enc.get("profile", "")
                full_name = f"Elite {enc_name} {enc_profile}".strip()
                
                registry["video_encoders"].append({
                    "id": enc_id,
                    "rebrandedName": full_name,
                    "originalEncoder": enc_name,
                    "profile": enc_profile,
                    "ffmpegOpts": enc.get("ffmpegOpts", "")
                })
    except Exception as e:
        print(f"Error parsing video-encoders: {e}")

    # 3. Parse Audio Codecs
    try:
        with open(os.path.join(MODELS_DIR, "audio-codecs.json"), 'r') as f:
            codecs = json.load(f)
            for cod in codecs:
                cod_id = cod.get("id", "")
                cod_name = cod.get("encoder", "Unknown")
                
                registry["audio_codecs"].append({
                    "id": cod_id,
                    "rebrandedName": f"Elite {cod_name}",
                    "ffmpegOpts": cod.get("ffmpegOpts", "")
                })
    except Exception as e:
        print(f"Error parsing audio-codecs: {e}")
        
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(registry, f, indent=4)
        
    print(f"Successfully generated {OUTPUT_FILE} with:")
    print(f"- {len(registry['models'])} AI Models")
    print(f"- {len(registry['video_encoders'])} Video Encoders")
    print(f"- {len(registry['audio_codecs'])} Audio Codecs")

if __name__ == "__main__":
    build_registry()
