# 여러 대의 컨테이너를 Master - Slave 관계로 테스트 하기

Master-Slave 관계를 이용해서 부하 테스트를 하려면, Master-Slave 컨테이너 간 통신이 가능해야 합니다. 이를 위해 서비스 검색 기능을 이용합니다. 
AWS 콘솔에서는 ECS 서비스를 생성할 때 서비스 검색 기능을 연동할 수 있고, Cloud Map에서 확인할 수 있습니다. 

## 서비스 검색을 위한 리소스 생성

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

## 보안 그룹 만들기

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

## Master 서비스 실행하기

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

## Slave 컨테이너 실행하기

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

## 리소스 정리하기

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