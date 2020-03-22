# 하나의 컨테이너로 테스트 하기

## Task 정의 생성하기

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
                {
                    "containerPort": 8089,
                    "protocol": "tcp"
                }
            ]
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
* `logConfiguration`: 기본적으로 CloudWatch Logs에 로그를 남깁니다. Stdout 및 stderr로 출력한 내용이 CloudWatch Logs에 담기게 됩니다. 
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

## 보안 그룹 생성

CLI로 보안 그룹을 하나 생성합니다. (콘솔을 이용하는 경우, 콘솔에서 보안 그룹을 생성할 수도 있습니다) 

Locust의 웹 인터페이스에 접속할 수 있도록 8089 포트를 외부에 개방합니다.

```shell script
aws ec2 create-security-group --description "Security Group for Locust Fargate Task" --group-name "Locust_Fargate_SG"
{
    "GroupId": "sg-(보안 그룹 ID)"
}
aws ec2 authorize-security-group-ingress --group-id sg-(보안 그룹 ID) --protocol tcp --port 8089 --cidr 0.0.0.0/0
```

## Task 실행하기

먼저 하나의 컨테이너로 테스트 해 보겠습니다. 

```shell script
aws ecs run-task --launch-type FARGATE --cluster (클러스터 이름) --count 1 \
--network-configuration 'awsvpcConfiguration={subnets=["서브넷 ID","다른 서브넷 ID"],securityGroups=["앞에서 만든 보안 그룹 ID"],assignPublicIp="ENABLED"}' \
--overrides file://./task-override.json --task-definition (Task 이름:버전)
```

여기서 `--overrides` 옵션에서 `task-override.json` 파일을 참조했는데요. 이 파일에는 원래의 Task 정의와 다르게 동작해야 하는 내용들을 여기에 적어 줍니다. 
예를 들면, 환경 변수가 추가되어야 한다거나, 다른 명령을 실행해야 한다거나, 기타 다른 옵션들이 있을 것 같습니다. 저는 이 파일에서 테스트 할 URL을 환경 변수로 넣어 주었습니다. 

자세한 내용은 AWS CLI Command Reference의 [run-task](https://docs.aws.amazon.com/cli/latest/reference/ecs/run-task.html) 항목에서 `--overrides` 옵션의 내용을 참조하세요.

어쨌든 위의 명령을 실행하면, 다음과 같은 내용이 출력됩니다.
```
{
    "tasks": [
        {
            "attachments": [
                {
                    "id": "...",
                    "type": "ElasticNetworkInterface",
                    "status": "PRECREATED",
                    "details": [
                        {
                            "name": "subnetId",
                            "value": "..."
                        }
                    ]
                }
            ],
            "availabilityZone": "ap-northeast-2a",
            "clusterArn": "arn:aws:ecs:ap-northeast-2:(계정 ID):cluster/(클러스터 이름)",
            "containers": [
                {
                    "containerArn": "arn:aws:ecs:ap-northeast-2:(계정 ID):container/....",
                    "taskArn": "arn:aws:ecs:ap-northeast-2:(계정 ID):task/(Task ID)",
            ... 이하 생략
```

이 중에서 `taskArn` 속성에 있는 값을 기억해 주세요.

여기서 어느 주소로 들어가야 Locust의 웹 인터페이스로 들어갈 수 있는지 확인이 필요합니다. 두 가지 방법이 있는데요. 

1. ECS 콘솔에서 실행 중인 Task를 찾아 Public IP를 찾는다.
2. `aws ecs describe-tasks --cluster (클러스터 이름) --tasks (Task ID)` 실행 후 연결된 ENI ID를 찾아 `aws ec2 describe-network-interfaces --network-interface-ids (ENI ID)`로 Public IP를 확인한다.

Public IP를 찾았다면, 웹 브라우저에서 `http://(Public IP 주소):8089`를 입력하여 Locust의 페이지를 열 수 있습니다.

## Task 종료하기 

Task 실행을 끝내려면 다음과 같이 입력합니다. 

```shell script
aws ecs stop-task --cluster (클러스터 이름) --task (Task ID)
```