#!/usr/bin/bash

ABSPATH=$(cd "$(dirname "$0")" || exit; pwd -P)
# create icons.iconset folder
[[ -d $ABSPATH/icons.iconset ]] || mkdir -p "$ABSPATH"/icons.iconset

echo "Creating temporary files..."
# create duplicates with the necessary naming format
for file in "$ABSPATH"/bl_[^l]*.png; do {
    base=$(basename "$file" .png)
    size=${base/.*bl_\([0-9]\+\)/\1/}
    size=${size/bl_/}
    cp "$file" "$ABSPATH"/icons.iconset/icon_"${size}"x"${size}".png
}; done

# create bl.icons file
echo "Creating bl.icns..."
iconutil -c icns "$ABSPATH"/icons.iconset -o "$ABSPATH"/bl.icns

# delete temporary folder
echo "Deleting temporary folder (""$ABSPATH""/icons.iconset)..."
rm -r "$ABSPATH"/icons.iconset