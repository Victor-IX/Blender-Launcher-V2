import os
import sys
import shutil

if sys.platform == "win32":
    destination_dir = os.path.join(os.getenv("LOCALAPPDATA"), "Blender Launcher")
elif sys.platform == "linux":
    destination_dir = os.path.expanduser("~/.config/Blender Launcher")
else:
    raise OSError("Unsupported operating system")

source_file = "./extras/Blender Launcher.ini"

if not os.path.exists(destination_dir):
    os.makedirs(destination_dir)
else:
    destination_file_path = os.path.join(destination_dir, "Blender Launcher.ini")
    if os.path.exists(destination_file_path):
        os.remove(destination_file_path)


if os.path.exists(source_file):
    shutil.copy2(source_file, destination_file_path)
    print(f"Updated config file in {destination_dir}")
else:
    print(f"{source_file} does not exist in the source directory")
