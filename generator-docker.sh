#!bash
docker run -it --rm -v $(pwd):/app $(docker build -q .)