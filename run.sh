docker build -t recipe-app .

docker run -it --rm -v "$PWD":/app recipe-app 

