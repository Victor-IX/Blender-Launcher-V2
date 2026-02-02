#!/bin/bash

# check if we need to move back to the root of the project folder
if [ "$(basename "$PWD")" = "scripts" ]; then
	cd ..
fi

PYTHONOPTIMIZE=2 pyinstaller \
	--hidden-import "pynput.keyboard._xorg" \
	--hidden-import "pynput.mouse._xorg" \
	--hidden-import "python-xlib" \
	--clean \
	--noconsole \
	--noupx \
	--onefile \
	--name="Blender Launcher" \
    --add-data="source/localization/*.yml:localization" \
	--add-binary="source/resources/certificates/custom.pem:files" \
	--add-data="source/resources/api/blender_launcher_api.json:files" \
	--distpath="./dist/release" \
	source/main.py
