#!/usr/bin/env python3
"""
DEPRECATED: Legacy Topaz Video AI API Integration.
==================================================
The external Topaz API / TopazVideoAnalyzer dependency has been fully DEPRECATED.
All video enhancement and mastering capabilities are now natively executed by the
sovereign HotnHazy / SSK DSP engine via embedded FFmpeg filter graphs (Apex, Lumina, Solstice).
"""
import os
import shutil
import sys
from pathlib import Path

# Connect native sovereign NLE engine
REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "windows"))
import engine as nle

def enhance_all_videos():
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    
    videos = [
        "/Volumes/Mac-Core/Media/Movies/copy_F42D491D-883F-4C7D-AB1D-532AF515D028.mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_3703.mp4",
        "/Volumes/Mac-Core/Media/Movies/copy_5C8223A4-64A0-4BB5-8F2E-456DC24E55A4.mp4",
        "/Volumes/Mac-Core/Media/Movies/copy_C3FF9E82-A537-46EE-8C4C-89CA6486E25F.mp4",
        "/Volumes/Mac-Core/Media/Movies/copy_48A34F85-6BF6-41DE-8B1D-99BD1EA81BC5 (1).mp4",
        "/Volumes/Mac-Core/Media/Movies/copy_48A34F85-6BF6-41DE-8B1D-99BD1EA81BC5 (2).mp4",
        "/Volumes/Mac-Core/Media/Movies/copy_48A34F85-6BF6-41DE-8B1D-99BD1EA81BC5 (4).mp4",
        "/Volumes/Mac-Core/Media/Movies/copy_48A34F85-6BF6-41DE-8B1D-99BD1EA81BC5.mp4",
        "/Volumes/Mac-Core/Media/Movies/copy_F4E167D9-9CAC-418E-B5B2-5778AC3B3D63 (1).mp4",
        "/Volumes/Mac-Core/Media/Movies/copy_F4E167D9-9CAC-418E-B5B2-5778AC3B3D63.mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_6944.mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_8213.mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_8214 (1).mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_8214.mp4",
        "/Volumes/Mac-Core/Media/Movies/copy_48A34F85-6BF6-41DE-8B1D-99BD1EA81BC5 (3).mp4",
        "/Volumes/Mac-Core/Media/Movies/copy_F4E167D9-9CAC-418E-B5B2-5778AC3B3D63 (2).mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_3581.mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_6943.mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_6945.mp4",
        "/Volumes/Mac-Core/Media/Movies/RenderedVideo.mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_3587.mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_7866.mp4",
        "/Volumes/Mac-Core/Media/Movies/ScreenRecording_04-08-2026 03-11-36_1.mp4",
        "/Volumes/Mac-Core/Media/Movies/copy_0DA41FF7-898E-459B-BD27-CD37C06987A2.mp4",
        "/Volumes/Mac-Core/Media/Movies/copy_789DAA95-E472-4861-AB27-6D8D14BDB3CF (1).mp4",
        "/Volumes/Mac-Core/Media/Movies/copy_789DAA95-E472-4861-AB27-6D8D14BDB3CF.mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_3582.mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_1858.mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_4186.mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_4187.mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_6942.mp4",
        "/Volumes/Mac-Core/Media/Movies/IMG_7864.mp4",
        "/Volumes/LSJ PROJECTS/copy_F4E167D9-9CAC-418E-B5B2-5778AC3B3D63.mov",
        "/Volumes/Mac-Core/1332_3.mp4",
        "/Volumes/Mac-Core/Documents/Unsorted/IMG_1641.MP4",
        "/Volumes/Mac-Core/Sorted_Videos/Person_01/1970-01-01/473_3.mp4",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2013-09-14/E3731AF1-9F83-4FE5-8F76-C3C3DC3B2EAA.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2017-05-03/5C5E04AC-295A-4692-9E02-D09ED23B0E01.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2017-07-20/11AF71D4-70BE-4E49-9DA1-9006AB3F98E5.mp4",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2017-07-20/3542B6F3-E46C-44EF-8D56-F38967C98F6D.mp4",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2017-07-20/EED4B38E-8619-4CCC-A84B-EBA3ED75F9EE.mp4",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2018-09-17/7E63D1C6-1370-4227-AD9D-0FF9E711DD57.mp4",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2018-11-16/1332_3.mp4",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2019-08-14/6A3D1312-4A9F-4501-AD4C-B67D96C0814A.mp4",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2020-11-20/AA524231-A777-4088-9031-1EDB1DDF61E2_2_0_a.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2022-11-08/09EBE1C1-E410-4D5A-95C7-D0C7E568D788.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2023-01-31/8BC91BC8-EEB2-43A0-AFE8-B298EB64C05A.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2024-06-17/A947D9D4-E5A6-4110-B474-B0C2B4F3CF68.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2024-06-24/9B522937-6FE3-49B9-9D22-F1B39CAC0A50.mp4",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2024-08-20/032E2717-5712-4D37-81CC-A2BAD30F78C1.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2025-02-13/2025-02-13 16.03.06.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2025-06-17/89791FF9-3DB0-4CB4-91DB-B772474B2B39.mov",
        "/Users/lsjsystemsconsulting/CEBCF73D-3D11-4ADA-A89E-1C5AB989FFE3_transcoded.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2025-07-10/09815E6D-CE93-4612-835A-67D4E83271A9.mp4",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2025-10-04/DC23F2F1-2073-4300-BD9C-00BCF091DC65_2_0_a.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2025-10-18/7F2CF563-D4E3-4B2A-8C5C-725992C7AD15_2_0_a.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2025-11-02/IMG_4189.MP4",
        "/Users/lsjsystemsconsulting/E19981CE-5DF8-42E4-9B30-1122E2DAF15A_2_0_a_transcoded.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2025-12-11/F1A88EDD-9B84-4D3F-95FA-D1B84D72CDF9.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2025-12-11/B6ABDBBD-63BA-45C9-A3AF-C6D1BE938DD3.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2025-12-22/0BCAAD6A-649B-4CD9-B7E5-5B54F32A2B2B.mp4",
        "/Volumes/Mac-Core/Sorted_Videos/Misc/2026-01-17/13D92701-FCF9-41F2-AED9-0E6E68152D1D.mov",
        "/Volumes/Mac-Core/Sorted_Videos/Person_01/1970-01-01/DDFD9B21-F6D9-4D91-8AB5-87BB8DA3FF73.mp4",
        "/Volumes/Mac-Core/Media/Pictures/Photos Library.photoslibrary/originals/D/DDFD9B21-F6D9-4D91-8AB5-87BB8DA3FF73.mp4"
    ]
    
    output_dir = "/Users/lsjsystemsconsulting/enhanced_videos"
    
    for video_path in videos:
        print(f"Enhancing {video_path}...")
        file_name = os.path.basename(video_path)
        output_path = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}_enhanced.mp4")
        
        ok, msg = nle.enhance(ffmpeg_bin, video_path, output_path)
        if not ok:
            print(f"Error enhancing {video_path}: {msg}")
        else:
            print(f"Successfully enhanced {video_path} to {output_path} via sovereign HotnHazy/SSK engine")

if __name__ == "__main__":
    enhance_all_videos()
    print("All videos have been processed.")
