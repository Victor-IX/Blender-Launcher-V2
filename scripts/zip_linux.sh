#!/usr/bin/bash

# check if we need to move back to the root of the project folder
if [ "$(basename "$PWD")" = "scripts" ]; then
    cd ..
fi

# get the distro and get the Title version
distro_id=$(python3 -c "import distro; print(distro.id().title())")
version=$1

echo "Zipping to Blender_Launcher_${version}_${distro_id}_x64.zip"
zip "Blender_Launcher_${version}_${distro_id}_x64.zip" "./dist/release/Blender Launcher" "./extras/blenderlauncher.desktop" "./source/resources/icons/bl/bl_128.png"
mv "Blender_Launcher_${version}_${distro_id}_x64.zip" ./dist/release/
