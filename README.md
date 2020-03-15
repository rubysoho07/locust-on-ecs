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

##### Windows에서 이미지 올리기 (Powershell 기준)

다른 명령은 모두 동일하나, 두번째 줄의 내용은 `Invoke-Expression -Command (aws ecr get-login --no-include-email)`으로 바꾸어 실행합니다.

### 로컬에서 이미지 실행해 보기

다음 명령으로 Docker Image를 실행합니다. 

```shell script
docker run -p 8089:8089 -e TARGET_URL=(테스트 하려고 하는 URL) (Docker 이미지 이름)
```

Linux/macOS의 경우 `localhost:8089`로, Windows의 경우 `가상 머신의 IP:8089`로 접속하여 Locust를 실행합니다. 

Docker 이미지를 종료할 때는 Container ID를 얻기 위해 `docker ps` 명령을 실행한 뒤, `docker kill (Container ID)`로 종료합니다. 

## ECS Task 및 클러스터 만들기

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

## ECS에서 테스트 하기

CLI로 보안 그룹을 하나 생성합니다. (콘솔을 이용하는 경우, 콘솔에서 보안 그룹을 생성할 수도 있습니다) 

Locust의 웹 인터페이스에 접속할 수 있도록 8089 포트를 외부에 개방합니다.

```shell script
aws ec2 create-security-group --description "Security Group for Locust Fargate Task" --group-name "Locust_Fargate_SG"
{
    "GroupId": "sg-(보안 그룹 ID)"
}
aws ec2 authorize-security-group-ingress --group-id sg-(보안 그룹 ID) --protocol tcp --port 8089 --cidr 0.0.0.0/0
```

### 하나의 컨테이너로 테스트 하기

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
                    "taskArn": "arn:aws:ecs:ap-northeast-2:(계정 ID):task/(클러스터 ID)/(Task ID)",
            ... 이하 생략
```

이 중에서 `taskArn` 속성에 있는 값을 기억해 주세요.

여기서 어느 주소로 들어가야 Locust의 웹 인터페이스로 들어갈 수 있는지 확인이 필요합니다. 두 가지 방법이 있는데요. 

1. ECS 콘솔에서 실행 중인 Task를 찾아 Public IP를 찾는다.
2. `aws ecs describe-tasks --cluster (클러스터 이름) --tasks (Task ID)` 실행 후 연결된 ENI ID를 찾아 `aws ec2 describe-network-interfaces --network-interface-ids (ENI ID)`로 Public IP를 확인한다.

Public IP를 찾았다면, 웹 브라우저에서 `http://(Public IP 주소):8089`를 입력하여 Locust의 페이지를 열 수 있습니다.

Task 실행을 끝내려면 다음과 같이 입력합니다. 

```shell script
aws ecs stop-task --cluster (클러스터 이름) --task (Task ID)
```

### 여러 대의 컨테이너를 Master - Slave 관계로 테스트 하기

Master-Slave 관계를 이용해서 부하 테스트를 하려면, Master-Slave 컨테이너 간 통신이 가능해야 합니다. 이를 위해 서비스 검색 기능을 이용합니다. 
AWS 콘솔에서는 ECS 서비스를 생성할 때 서비스 검색 기능을 연동할 수 있고, Cloud Map에서 확인할 수 있습니다. 

#### 서비스 검색을 위한 리소스 생성

서비스 검색 기능을 이용하기 위해, 서비스 검색과 관련된 리소스를 생성합니다. 

먼저 Private 서비스 검색 네임스페이스를 생성합니다. 

```shell script
aws servicediscovery create-private-dns-namespace --name (Namespace 이름) --vpc (VPC ID) --region ap-northeast-2
```

결과로 나온 값의 `OperationId` 값을 참조하여 성공적으로 생성되었는지 확인합니다.

```shell script
aws servicediscovery get-operation --operation-id (앞에서 가져온 Operation ID)
```

결과 중에 `Targets` 내에 있는 `NAMESPACE` 부분의 값을 복사합니다.
 
이제 Master 컨테이너에서 사용할 서비스를 다음과 같이 생성합니다. 

```shell script
aws servicediscovery create-service --name locust-master --dns-config 'NamespaceId="(Namespace ID)",DnsRecords=[{Type="A",TTL="300"}]' --health-check-custom-config FailureThreshold=1
{
    "Service": {
        "Id": "(Service Discovery 서비스 ID)",
        "Arn": "arn:aws:servicediscovery:ap-northeast-2:(계정 ID):service/(Service Discovery에 등록한 서비스 ID)",
        "Name": "(Namespace 이름)",
        "NamespaceId": "(Namespace ID)",
        "DnsConfig": {
            "NamespaceId": "(Namespace ID)",
            "RoutingPolicy": "MULTIVALUE",
... (생략)
    }
}
```

결과에서 `Service` Object 안에 있는 `Id` 값을 복사합니다. 

#### 보안 그룹 만들기

다음과 같은 명령을 실행합니다. 각 포트의 의미는 다음과 같습니다.

* 8089: 웹으로 통신하기 위한 포트
* 5557, 5558: Master - Slave 컨테이너 간 통신을 위한 포트

```shell script
aws ec2 create-security-group --description "Security Group for Locust Fargate Task" --group-name "Locust_Fargate_Master_SG"
{
    "GroupId": "sg-(보안 그룹 ID)"
}
aws ec2 authorize-security-group-ingress --group-id sg-(보안 그룹 ID) --protocol tcp --port 8089 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id sg-(보안 그룹 ID) --protocol tcp --port 5557 --cidr (IP 대역/서브넷 마스크)
aws ec2 authorize-security-group-ingress --group-id sg-(보안 그룹 ID) --protocol tcp --port 5558 --cidr (IP 대역/서브넷 마스크)
```

#### Master 서비스 실행하기

Master 역할을 하는 서비스는 8089, 5557, 5558 포트를 열어야 합니다. (어떤 의미인지는 앞에서 설명해 드렸습니다) 

그리고 환경 변수로 `LOCUST_MODE`를 추가하여 `master`로 설정해야 합니다. 

그런데 Task 설정 시 overrides 설정으로는 포트를 추가로 개방할 수 없습니다. 그래서 다른 Task 정의를 만들어야 합니다. 새로운 Task 정의는 `task-definition-master.json`파일을 참고해 주세요. 

달라진 부분은 다음과 같습니다. 
* `portMappings`: 8089, 5557, 5558 포트를 매핑합니다.
* `environment`: `LOCUST_MODE` 환경변수가 추가되었습니다. Master 모드로 사용하기 위해 `master`로 설정합니다.

이제 Task 정의를 생성해 보겠습니다. 
```shell script
aws ecs register-task-definition --cli-input-json file://./task-definition-master.json
``` 

별 탈 없이 Task 정의가 생성되었다면, 서비스를 생성하기 전에 `locust-service-master.json` 파일을 열어봅니다. 
```
{
    "cluster": "(클러스터 이름)",                   // ECS 클러스터 이름
    "serviceName": "(서비스 이름)",                 // 서비스 이름
    "taskDefinition": "(Task 이름:버전)",           // Task 정의
    "serviceRegistries": [                          // 앞에서 만든 Service Discovery의 서비스와 연결
       {
          "registryArn": "arn:aws:servicediscovery:ap-northeast-2:(계정 ID):service/(Service Discovery에 등록한 서비스 ID)"
       }
    ],
    "launchType": "FARGATE",
    "platformVersion": "LATEST",
    "networkConfiguration": {                       // 네트워크 설정
       "awsvpcConfiguration": {
          "assignPublicIp": "ENABLED",
          "securityGroups": [ "(보안 그룹 ID)" ],
          "subnets": [ "(서브넷 ID)", "(다른 서브넷 ID)" ]
       }
    },
    "desiredCount": 1                               // 1개의 컨테이너만 실행
}
```

내용을 확인하고 적절히 수정한 뒤, 본격적으로 서비스를 생성합니다.
```shell script
aws ecs create-service --cli-input-json file://./locust-service-master.json
```

이제 Master 서비스가 어떤 DNS 레코드로 등록되어있는지 확인해 봅시다. 

```shell script
aws servicediscovery get-namespace --id (Namespace ID) --region ap-northeast-2
{
    "Namespace": {
        "Id": "(Namespace ID)",
        "Arn": "arn:aws:servicediscovery:ap-northeast-2:(계정 ID):namespace/(Namespace ID)",
        "Name": "(Namespace 이름)",
        "Type": "DNS_PRIVATE",
        "Properties": {
            "DnsProperties": {
                "HostedZoneId": "(Host Zone ID)"
            },
```

여기서 `HostedZoneId` 속성 값을 찾아 메모한 뒤, 다음과 같이 입력합니다. 

```shell script
aws route53 list-resource-record-sets --hosted-zone-id (Host Zone ID) --region ap-northeast-2
{
    "ResourceRecordSets": [
        ... (중간 생략)
        {
            "Name": "(Master 서비스 이름).(Namespace 이름).",
            "Type": "A",
... (아래 생략)
}
```

그러면 `Master 서비스 이름.Namespace 이름`과 같은 방식으로 등록되어 있는 것을 볼 수 있습니다. 

#### Slave 컨테이너 실행하기

Master와 Slave 컨테이너 모두 동일한 스크립트를 가지고 있어야 하므로, 앞에서 만든 master의 작업 정의를 활용해서 작업을 생성해 보겠습니다. Slave 역할을 하는 컨테이너는 다음과 같은 차이가 있습니다. 

* `LOCUST_MODE` 환경 변수: `slave`로 설정
* `LOCUST_MASTER_HOST` 환경 변수: 앞에서 얻어온 Master DNS의 정보 (`Master 서비스 이름.Namespace 이름`과 같은 형식)

`task-override-slave.json` 파일을 확인해 보시면, 어떤 부분이 달라졌는지 확인하실 수 있습니다.
```
{
  "containerOverrides": [
    {
      "name": "(Task 이름)",
      "environment": [
... (앞부분 생략)
        {
          "name": "LOCUST_MODE",
          "value": "slave"
        },
        {
          "name": "LOCUST_MASTER_HOST",
          "value": "Master 서비스 이름.Namespace 이름"
        }
      ]
    }
  ]
}
``` 

본격적으로 작업 정의를 활용해서 Task를 실행해 보겠습니다.
```shell script
aws ecs run-task --launch-type FARGATE --cluster (클러스터 이름) --count 2 \
--network-configuration 'awsvpcConfiguration={subnets=["서브넷 ID","다른 서브넷 ID"],securityGroups=["앞에서 만든 보안 그룹 ID"],assignPublicIp="ENABLED"}' \
--overrides file://./task-override-slave.json --task-definition (Task 이름:버전)
```

조금 기다렸다가 `Master의 Public IP:8089` 주소로 접속해 보면, Slave 개수가 2인 것을 확인할 수 있습니다. 

이제 테스트를 진행해 볼 수 있습니다. 

#### 리소스 정리하기

실행 중인 서비스를 종료한 뒤 삭제합니다.
```shell script
aws ecs update-service --cluster (클러스터 이름) --service (서비스 이름) --desired-count 0 
aws ecs delete-service --cluster (클러스터 이름) --service (서비스 이름)
```

그리고 slave 작업들을 모두 종료합니다.
```shell script
aws ecs list-tasks --cluster (클러스터 이름) --family locust-master
{
    "taskArns": [
        "arn:aws:ecs:ap-northeast-2:(계정 ID):task/(클러스터 이름)/(Task ID 1)",
        "arn:aws:ecs:ap-northeast-2:(계정 ID):task/(클러스터 이름)/(Task ID 2)"
    ]
}
aws ecs stop-task --cluster (클러스터 이름) --family (Task ID 1)
aws ecs stop-task --cluster (클러스터 이름) --family (Task ID 2)
```

서비스 검색 내 등록된 서비스를 삭제합니다.
```shell script
aws servicediscovery delete-service --id (Service Discovery에 등록한 서비스 ID)
```

서비스 검색 네임스페이스를 삭제합니다.
```shell script
aws servicediscovery delete-namespace --id (Namespace ID)
```

ECS 클러스터를 삭제합니다.
```shell script
aws ecs delete-cluster --cluster (클러스터 이름)
```

ECR에 이미지를 올린 경우, ECR의 저장소도 삭제합니다. (`--force` 옵션은 저장소 내 이미지가 있더라도 무조건 삭제합니다.)
```shell script
aws ecr delete-repository --repository-name (저장소 이름) --force
```

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