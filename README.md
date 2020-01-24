# Locust on ECS

부하 테스트 환경을 구축하기 위해 ECS와 Locust를 사용하는 예제입니다.

## 개발 환경 구축

필요한 패키지 설치 

```shell script
pip install locustio
pip install awscli            # AWS CLI가 설치되어 있지 않은 경우
```

## Locust 스크립트 만들기

샘플 스크립트는 동일 폴더 내 `locust-example.py` 파일을 참고해 주세요.

Locust를 로컬에서 실행할 때는 다음과 같이 입력합니다. 

```shell script
locust -f (파일 이름) -H (호스트 이름)
```

기본적으로 웹브라우저에서 http://localhost:8089 주소로 접속하면 웹으로 테스트를 진행할 수 있습니다. 

## Docker 이미지 만들기

다음과 같이 Dockerfile을 만듭니다. (첨부한 Dockerfile을 참고하세요)

```dockerfile
FROM locustio/locust

ADD '스크립트 파일 이름' locustfile.py
```

Locust Docker 이미지는 기본적으로 `/locustfile.py` 파일을 찾아서 실행합니다.

만약 Locust 스크립트를 다른 이름으로 만들었다면, Docker 이미지 실행 시 `LOCUSTFILE_PATH` 환경변수에 스크립트 경로를 지정해 주어야 합니다.

그리고 다음과 같이 이미지를 빌드합니다.  

```shell script
docker build -t (ID)/(이미지 이름:태그) .
```

### 이미지 올리기

Docker Hub에 이미지를 올리는 경우, 다음과 같이 진행합니다.
```shell script
docker login
docker push (ID)/(이미지 이름:태그)
```

ECR에 이미지를 올리는 경우, 다음과 같이 진행합니다. (ECR 콘솔에서 이미지 push를 위해 실행해야 하는 명령을 확인할 수 있습니다.) 

#### Linux나 macOS에서 이미지 올리기

```shell script
aws ecr create-repository --repository-name (저장소 이름)
$(aws ecr get-login --no-include-email --region ap-northeast-2)
docker build -t (저장소 이름) .
docker tag (저장소 이름):latest (계정 ID).dkr.ecr.ap-northeast-2.amazonaws.com/(저장소 이름):latest
docker push (계정 ID).dkr.ecr.ap-northeast-2.amazonaws.com/(저장소 이름):latest
```

#### Windows에서 이미지 올리기 (Powershell 기준)

다른 명령은 모두 동일하나, 두번째 줄의 내용은 `Invoke-Expression -Command (aws ecr get-login --no-include-email)`으로 바꾸어 실행합니다.

## ECS Task 및 클러스터 만들기



## ECS에서 테스트 하기


