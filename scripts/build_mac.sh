#!/bin/bash

# check if we need to move back to the root of the project folder
if [ "$(basename "$PWD")" = "scripts" ]; then
    cd ..
fi


PYTHONOPTIMIZE=2 pyinstaller \
    --windowed \
    --icon "source/resources/icons/bl/bl.icns" \
    --hidden-import "pynput.keyboard._darwin" \
    --hidden-import "pynput.mouse._darwin" \
    --name="Blender Launcher" \
    --add-binary="source/resources/certificates/custom.pem:files" \
    --add-data="source/resources/api/blender_launcher_api.json:files" \
    --distpath="./dist/release" \
    source/main.py

# To create a disk image, uncomment these:
# illusional: not creating a .dmg because it ballooned the size of the app (to roughly 150MB, .zip is ~35MB).
# [[ -d ./dist/release/dimg ]] || mkdir ./dist/release/dimg
# cp -r "./dist/release/Blender Launcher.app" "./dist/release/dimg/Blender Launcher.app"
# [[ -d ./dist/release/dimg/Applications ]] || ln -s "/Applications" "./dist/release/dimg/Applications"
# hdiutil create -volname BLV2 -srcfolder ./dist/release/dimg/ -ov "./dist/release/Blender Launcher.dmg"