#!/bin/bash

# check if we need to move back to the root of the project folder
if [ "$(basename "$PWD")" = "scripts" ]; then
    cd ..
fi

cd docs
mkdocs serve
