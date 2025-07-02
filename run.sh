docker build -t recipe-app .

docker run -it --rm -v "$PWD":/app -p 8501:8501 -p 11434:11434 recipe-app
