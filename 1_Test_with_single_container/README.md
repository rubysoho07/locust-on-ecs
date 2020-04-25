# 하나의 컨테이너로 테스트 하기

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