#!/bin/bash

# check if we need to move back to get to the docs folder
if [ "$(basename "$PWD")" = "scripts" ]; then
    cd ../docs || exit
else
    cd ./docs || exit
fi

mkdocs gh-deploy