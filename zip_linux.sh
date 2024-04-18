#!/usr/bin/bash

# get the distro and get the Title version
distro_id=$(python3 -c "import distro; print(distro.id().title())")
version=$1

echo "Zipping to Blender_Launcher_${version}_${distro_id}_x64.zip"
cd ./dist/release/ || exit
zip "Blender_Launcher_${version}_${distro_id}_x64.zip" "./Blender Launcher" "./extras/blenderlauncher.desktop" "./source/resources/icons/bl/bl_128.png"
