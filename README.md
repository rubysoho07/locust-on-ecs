# Locust on ECS

부하 테스트 환경을 구축하기 위해 ECS와 Locust를 사용하는 예제입니다. (모든 설명은 서울 리전(`ap-northeast-2`)을 기준으로 합니다.)

## 개발 환경 구축

*AWS CLI를 설치하지 않았다면, 다음 문서를 참고하여 설정해 주세요.*
* [AWS CLI 설치](https://docs.aws.amazon.com/ko_kr/cli/latest/userguide/install-cliv2.html)
* [AWS CLI 구성](https://docs.aws.amazon.com/ko_kr/cli/latest/userguide/cli-chap-configure.html)

Python과 pip가 설치되어 있다면, 다음 명령으로 locust를 설치합니다.
```shell script
pip install locustio
```

## Locust 스크립트 만들기

샘플 스크립트는 `0_Sample_Docker_Image/locust-example.py` 파일을 참고해 주세요.

Locust를 로컬에서 실행할 때는 다음과 같이 입력합니다. 

```shell script
locust -f (파일 이름) -H (호스트 이름)
```

기본적으로 웹브라우저에서 http://localhost:8089 주소로 접속하면 웹으로 테스트를 진행할 수 있습니다. 

## Docker 이미지 만들기

다음과 같이 Dockerfile을 만듭니다. (`0_Sample_Docker_Image/Dockerfile` 파일을 참고하세요)

```dockerfile
FROM locustio/locust

ADD '스크립트 파일 이름' locustfile.py

ENV TARGET_URL (테스트 할 URL)
```

Locust Docker 이미지는 기본적으로 `/locustfile.py` 파일을 찾아서 실행합니다.

만약 Locust 스크립트를 `/locustfile.py` 말고 다른 이름으로 복사했다면, Docker 이미지 실행 시 `LOCUSTFILE_PATH` 환경변수에 스크립트 경로를 지정해 주어야 합니다.

그리고 다음과 같이 이미지를 빌드합니다.  

```shell script
docker build -t (ID)/(이미지 이름:태그) .
```

### 이미지 올리기

#### Docker Hub에 이미지 올리기

Docker Hub에 이미지를 올리는 경우, 다음과 같이 진행합니다. (먼저 Docker Hub에 계정을 만들어 주세요)
```shell script
docker login
docker push (ID)/(이미지 이름:태그)
```

#### ECR에 이미지 올리기

ECR에 이미지를 올리는 경우, 다음과 같이 진행합니다. (ECR 콘솔에서 이미지 push를 위해 실행해야 하는 명령을 확인할 수 있습니다.) 

##### Linux나 macOS에서 이미지 올리기

```shell script
aws ecr create-repository --repository-name (저장소 이름)
$(aws ecr get-login --no-include-email --region ap-northeast-2)
docker build -t (저장소 이름) .
docker tag (저장소 이름):latest (계정 ID).dkr.ecr.ap-northeast-2.amazonaws.com/(저장소 이름):latest
docker push (계정 ID).dkr.ecr.ap-northeast-2.amazonaws.com/(저장소 이름):latest
```

최신 버전의 AWS CLI를 이용하는 경우, ECR에 로그인하는 명령이 변경되었습니다. 

```shell script
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin aws_account_id.dkr.ecr.ap-northeast-2.amazonaws.com
```

##### Windows에서 이미지 올리기 (Powershell 기준)

다른 명령은 모두 동일하나, 두번째 줄의 내용은 `Invoke-Expression -Command (aws ecr get-login --no-include-email)`으로 바꾸어 실행합니다.

최신 버전의 AWS CLI를 이용하는 경우, [PowerShell용 AWS 도구](https://aws.amazon.com/ko/powershell/)를 설치한 뒤, 다음 명령을 입력합니다.

```shell script
(Get-ECRLoginCommand).Password | docker login --username AWS --password-stdin aws_account_id.dkr.ecr.ap-northeast-2.amazonaws.com
```

### 로컬에서 이미지 실행해 보기

다음 명령으로 Docker Image를 실행합니다. 

```shell script
docker run -p 8089:8089 (Docker 이미지 태그)
```

Linux/macOS의 경우 `localhost:8089`로, Windows의 경우 `가상 머신의 IP:8089`로 접속하여 Locust를 실행합니다. 

Docker 이미지를 종료할 때는 Container ID를 얻기 위해 `docker ps` 명령을 실행한 뒤, `docker kill (Container ID)`로 종료합니다. 

## ECS 클러스터 및 Task 정의 만들기

### ECS 클러스터 만들기

다음 명령을 입력하여 클러스터를 만듭니다. `--cluster-name` 옵션에 아무 값도 없다면 `default` 클러스터가 생성됩니다.

```shell script
aws ecs create-cluster --cluster-name (클러스터 이름)
```

성공 시 결과는 다음과 같습니다.

```
{
    "cluster": {
        "clusterArn": "arn:aws:ecs:ap-northeast-2:(계정 ID):cluster/(클러스터 이름)",
        "clusterName": "(클러스터 이름)",
        "status": "ACTIVE",
        ... (아래 생략)
    }
}
```

### ECS Task 정의 만들기

#### ECS가 Task를 실행할 수 있는 IAM Role 만들기

시작하기 전에, ECS가 사용자를 대신해서 Task를 실행할 수 있는 역할을 만들어야 합니다.

다음 튜토리얼의 **1단계만** 진행하세요.

[AWS ECS CLI를 사용하여 Fargate 작업이 있는 클러스터 생성](https://docs.aws.amazon.com/ko_kr/AmazonECS/latest/developerguide/ecs-cli-tutorial-fargate.html)

#### 진짜로 Task 정의 생성하기

작업 정의를 CLI에서 생성하려면, 필요한 설정들을 JSON 파일 또는 CLI 명령에 넣어야 합니다. 
이번 예제에서는 `task-definition.json` 파일을 이용해서 Fargate 작업 정의를 생성해 보겠습니다. 

`task-definition.json` 파일의 내용은 다음과 같습니다. `()` 안에 있는 내용은 적절히 바꿔주세요.

(아래 예제는 이미지가 ECR에 있는 경우를 가정합니다. Docker Hub에 있다면 `(사용자 ID)/(이미지 이름)` 등으로 수정해 주세요)

```json
{
    "requiresCompatibilities": [
        "FARGATE"
    ],
    "inferenceAccelerators": [],
    "containerDefinitions": [
        {
            "name": "(Task 이름)",
            "image": "(계정 ID).dkr.ecr.ap-northeast-2.amazonaws.com/(저장소 이름)",
            "portMappings": [
                { "containerPort": 8089, "protocol": "tcp" }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/(Task 이름)",
                    "awslogs-region": "ap-northeast-2",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ],
    "networkMode": "awsvpc",
    "memory": "2048",
    "cpu": "1024",
    "executionRoleArn": "(앞에서 만든 IAM Role)",
    "family": "(Task 이름)",
    "taskRoleArn": ""
}
```

몇 가지 속성을 살펴보겠습니다. 

* `requiresCompatibilities`: Fargate를 이용하기 위해 `FARGATE`로 설정합니다.
* `portMappings`: 컨테이너와 호스트 포트 간 매핑입니다. 8089번 포트를 이용하면 Locust의 웹 콘솔로 이동할 수 있기 때문에 8089 포트에 대해 설정했습니다. 
* `logConfiguration`: CloudWatch Logs에 로그를 남깁니다. Stdout 및 stderr로 출력한 내용이 CloudWatch Logs에 담기게 됩니다. (로그 그룹은 미리 생성해야 합니다.)
* `memory`, `cpu`: 컨테이너에서 사용할 메모리와 CPU의 조합입니다. 어떻게 설정해야 하는지 궁금하다면, [이 문서](https://docs.aws.amazon.com/ko_kr/AmazonECS/latest/developerguide/create-task-definition.html)를 참고하세요.

그리고 CLI에서 다음과 같이 Task 정의를 만듭니다. 

```shell script
aws ecs register-task-definition --cli-input-json file://./task-definition.json
```

성공한다면 아래와 같은 결과를 보실 수 있습니다.
```
{
    "taskDefinition": {
        "taskDefinitionArn": "arn:aws:ecs:ap-northeast-2:(계정 ID):task-definition/(Task 이름:버전)",
        "containerDefinitions": [
            {
                "name": "locust-test",
                "image": "(계정 ID).dkr.ecr.ap-northeast-2.amazonaws.com/(저장소 이름)",
                ... (아래 생략)
    }
}
```

## ECS에서 테스트 하기

### 하나의 컨테이너로 테스트 하기

[문서 참조](1_Test_with_single_container/README.md)

### 여러 대의 컨테이너를 Master - Slave 관계로 테스트 하기

[문서 참조](2_Test_with_master_slave/README.md)

## 참고한 자료들

* [Amazon ECR에서 AWS CLI 사용](https://docs.aws.amazon.com/ko_kr/AmazonECR/latest/userguide/ECR_AWSCLI.html)
* [Running Locust with Docker](https://docs.locust.io/en/stable/running-locust-docker.html#running-locust-docker)
* [Task Networking in AWS Fargate](https://aws.amazon.com/ko/blogs/compute/task-networking-in-aws-fargate/)
* [AWS CLI 매뉴얼 - ecs register-task-definition](https://docs.aws.amazon.com/cli/latest/reference/ecs/register-task-definition.html)
* [AWS CLI를 이용하여 Fargate 작업이 있는 클러스터 생성](https://docs.aws.amazon.com/ko_kr/AmazonECS/latest/developerguide/ECS_AWSCLI_Fargate.html)
* [작업 정의 생성하기](https://docs.aws.amazon.com/ko_kr/AmazonECS/latest/developerguide/create-task-definition.html)
* [AWS CLI 매뉴얼 - ec2 create-security-group](https://docs.aws.amazon.com/cli/latest/reference/ec2/create-security-group.html)
* [AWS CLI 매뉴얼 - authorize-security-group-ingress](https://docs.aws.amazon.com/cli/latest/reference/ec2/authorize-security-group-ingress.html)
* [AWS CLI 매뉴얼 - ecs run-task](https://docs.aws.amazon.com/cli/latest/reference/ecs/run-task.html)
* [How to run AWS ECS Task overriding environment variables](https://stackoverflow.com/questions/41373167/how-to-run-aws-ecs-task-overriding-environment-variables)
* [서비스 검색](https://docs.aws.amazon.com/ko_kr/AmazonECS/latest/developerguide/service-discovery.html)
* [자습서: 서비스 검색을 사용하여 서비스 생성](https://docs.aws.amazon.com/ko_kr/AmazonECS/latest/developerguide/create-service-discovery.html)