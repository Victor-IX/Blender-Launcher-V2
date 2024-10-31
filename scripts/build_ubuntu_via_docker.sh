#!/bin/bash

# check if we need to move back to the root of the project folder
if [ "$(basename "$PWD")" = "scripts" ]; then
    cd ..
fi

# Comment these out to skip building the docker image
echo "Building blv2 docker image"
docker build -t blv2 .

echo "Launching blv2 image"
container=$(docker run -dit blv2)

echo "Copying the root of the project to the container"
docker container cp . $container:/blv2 || exit

echo "Launching blv2 build script"
docker exec $container bash scripts/build_linux.sh || exit

echo "Copying build to dist"
docker container cp $container:/blv2/dist . || exit

echo "Stopping the container"
docker stop $container || exit