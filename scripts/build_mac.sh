cd..
PYTHONOPTIMIZE=2 pyinstaller \
    --windowed \
    --icon "source/resources/icons/bl/bl.icns" \
    --hidden-import "pynput.keyboard._darwin" \
    --hidden-import "pynput.mouse._darwin" \
    --name="Blender Launcher" \
    --add-binary="source/resources/certificates/custom.pem:files" \
    --distpath="./dist/release" \
    source/main.py

# To create a disk image, uncomment these:
# [[ -d ./dist/release/dimg ]] || mkdir ./dist/release/dimg
# cp -r "./dist/release/Blender Launcher.app" "./dist/release/dimg/Blender Launcher.app"
# [[ -d ./dist/release/dimg/Applications ]] || ln -s "/Applications" "./dist/release/dimg/Applications"
# hdiutil create -volname BLV2 -srcfolder ./dist/release/dimg/ -ov "./dist/release/Blender Launcher.dmg"