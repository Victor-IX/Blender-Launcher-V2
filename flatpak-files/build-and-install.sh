#!/bin/sh

# Builds the flatpak while installing required dependencies and installs it in your user folder.

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" > /dev/null && pwd )
cd "$SCRIPT_DIR" || exit

YML_FILENAME="io.github.Victor_IX.Blender-Launcher-V2.yml"


if command -v flatpak-builder > /dev/null 2>&1; then
    cmd="flatpak-builder --force-clean flatpak-build-dir --install-deps-from flathub ${YML_FILENAME} --user --install"
elif command -v flatpak > /dev/null 2>&1; then
    if ! flatpak info org.flatpak.Builder > /dev/null 2>&1; then
        echo
        echo "org.flatpak.Builder not found. Please install it:"
        echo "flatpak install org.flatpak.Builder"
        exit 1
    fi
    cmd="flatpak run --command=flathub-build org.flatpak.Builder --force-clean  --user --install ${YML_FILENAME}"
else
    echo "Neither flatpak-builder nor flatpak were found."
    exit 1
fi

$cmd
