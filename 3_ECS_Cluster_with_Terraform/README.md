# Terraform으로 전체 환경을 한 번에 구성하기

Terraform으로 ECS 클러스터와 master 역할을 할 컨테이너까지 구성해 봅시다. 

먼저 cluster.tf, task-definition.json, slave_tasks.py 파일에 있는 다음 내용을 변경해 주세요.

* 서브넷 ID: master, slave task가 올라갈 서브넷 ID로 변경해 주세요.
* 이미지 경로: 앞 단계에서 만들었던 Locust Docker 이미지로 변경해 주세요.

## Terraform으로 ECS 클러스터 및 master 서비스 구성하기

```shell script
$ terraform init
$ terraform apply
```

리전을 물어보는 경우 `ap-northeast-2`(서울 리전)와 같이 적어줍니다. 리소스를 생성할 것인지 물어보면 `yes`를 입력해서 리소스를 생성합니다.

모든 과정이 끝나면, slave_tasks.py 파일의 내용 중 다음을 변경해 주세요.

* 보안그룹 ID: Terraform 구성 후 출력되는 security_group_id 값으로 변경

## Slave Task 시작하고 종료하기

같은 디렉터리에 있는 `slave_tasks.py` 파일을 이용하면 slave 역할을 할 task를 생성하고 종료할 수 있습니다.

boto3 라이브러리가 설치되어 있지 않다면, `pip install boto3` 또는 `pip install -r requirements.txt`를 먼저 실행해 주세요. 

* 시작할 때: `python slave_tasks.py --start (slave 개수)`
    * 지정한 개수만큼 slave task를 생성합니다.
* 종료할 때: `python slave_tasks.py --exit`
    * Master 역할을 하는 서비스 task를 제외한 모든 slave task를 종료합니다.

## Master의 Public IP 얻어오기

터미널에서 다음 명령을 입력합니다. 

```shell script
$ python slave_tasks.py --get-master-address
```

위 명령의 실행 결과를 메모한 뒤 웹 브라우저에서 `(Public IP 주소):8089`를 입력하면 Locust를 실행할 수 있습니다.
    
## 모든 리소스 삭제하기

터미널에서 다음을 입력합니다.

```shell script
$ terraform destroy
```

진짜로 모든 리소스를 삭제할 것인지 물어보면 `yes`를 입력합니다.