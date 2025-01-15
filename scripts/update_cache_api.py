import os
import sys
import json
import subprocess

if sys.platform == "win32":
    source_dir = os.path.join(os.getenv("LOCALAPPDATA"), "Blender Launcher")
elif sys.platform == "linux":
    source_dir = os.path.expanduser("~/.config/Blender Launcher")
else:
    raise OSError("Unsupported operating system")

destination_dir = os.path.join("source", "resources", "api")

files = {
    "stable_builds_linux.json": "stable_builds_api_linux.json",
    "stable_builds_Windows.json": "stable_builds_api_windows.json",
    "stable_builds_macOS.json": "stable_builds_api_macos.json",
}

for source_file, destination_file in files.items():
    source_file_path = os.path.join(source_dir, source_file)
    destination_file_path = os.path.join(destination_dir, destination_file)

    if os.path.exists(source_file_path):
        try:
            with open(source_file_path, "r") as src_file:
                source_data = json.load(src_file)

            if os.path.exists(destination_file_path):
                with open(destination_file_path, "r") as dest_file:
                    destination_data = json.load(dest_file)

                version = destination_data.get("api_file_version", "1.0")
                major_version = int(version.split(".")[0]) + 1
                destination_data["api_file_version"] = f"{major_version}.0"

                destination_data.update(source_data)
            else:
                destination_data = source_data
                destination_data["api_file_version"] = "1.0"

            with open(destination_file_path, "w") as dest_file:
                json.dump(destination_data, dest_file, indent=4)

            # Use git to check if the file has been modified (not only the file verison)
            result = subprocess.run(["git", "diff", "--numstat", destination_file_path], capture_output=True, text=True)
            modified_lines = sum(int(line.split()[0]) for line in result.stdout.splitlines())

            if modified_lines <= 1:
                subprocess.run(["git", "checkout", "--", destination_file_path])
                print(f"Reverted changes in {destination_file_path}, no new vesrion.")
            else:
                print(f"Updated {source_file_path} in {destination_dir}")
        except Exception as e:
            print(f"Failed to update {destination_file_path}: {e}")
    else:
        print(f"{source_file_path} does not exist in the source directory")
