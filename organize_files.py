import os
import shutil
import time

def main():
    directory = "/Volumes/LSJ PROJECTS"
    new_dir = os.path.join(directory, "New")
    old_dir = os.path.join(directory, "Old")

    # Create the directories if they don't exist
    if not os.path.exists(new_dir):
        os.makedirs(new_dir)
    if not os.path.exists(old_dir):
        os.makedirs(old_dir)

    # Calculate timestamp for 30 days ago
    current_time = time.time()
    thirty_days_in_seconds = 30 * 24 * 60 * 60
    threshold_time = current_time - thirty_days_in_seconds

    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)

        # Skip the directories we just created and any hidden files
        if item in ["New", "Old", "Do1o and Quan"] or item.startswith('.'):
            continue

        if os.path.isfile(item_path):
            file_mtime = os.path.getmtime(item_path)

            try:
                if file_mtime >= threshold_time:
                    shutil.move(item_path, os.path.join(new_dir, item))
                    print(f"Moved to New: {item}")
                else:
                    shutil.move(item_path, os.path.join(old_dir, item))
                    print(f"Moved to Old: {item}")
            except Exception as e:
                print(f"Error moving {item}: {e}")

if __name__ == "__main__":
    main()
