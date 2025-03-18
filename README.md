<!-- Tracking Token -->
![Security Notice](https://canarytokens.org/nest/assets/web-CYHNWdqG.png) Unauthorized use prohibited.

## chatbot_cj
https://canarytokens.org/nest/assets/web-CYHNWdqG.png

### dockerfile build 방법
docker build -t chat-api .

* 프로젝트 최상위 폴더에서 위 명령어 실행해 주세요!!!

### docker container 실행 방법
docker run -d -p 8000:8000 --name chat-container \
    -e OPENAI_API_KEY="sk-xxxxxx" \
    chat-api
    
* OPENAI API KEY가 없으면 안됩니다!!!
