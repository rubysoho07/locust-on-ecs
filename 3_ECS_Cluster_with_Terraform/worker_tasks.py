import argparse

import boto3


def stop_worker_tasks():
    """ Stop Worker ECS Tasks """
    print('Stop Tasks')
    ecs = boto3.client('ecs')

    tasks_list = ecs.list_tasks(
        cluster='Fargate_Load_Test_Cluster',
        family='LOCUST'
    )

    tasks = ecs.describe_tasks(
        cluster='Fargate_Load_Test_Cluster',
        tasks=tasks_list['taskArns']
    )

    for task in tasks['tasks']:
        if 'startedBy' not in task.keys():
            response = ecs.stop_task(cluster='Fargate_Load_Test_Cluster', task=task['taskArn'])
            print(response['task']['taskArn'], 'STOPPED')


def _get_master_private_ip(attachments: dict):
    """ Get private IP address of master service. """
    for detail in attachments['details']:
        if detail['name'] == 'privateIPv4Address':
            return detail['value']


def start_worker_tasks(count: int):
    """ Start Worker ECS Tasks """
    print(f'Start Worker Tasks: {count}')
    ecs = boto3.client('ecs')

    task = ecs.list_tasks(
        cluster='Fargate_Load_Test_Cluster',
        serviceName='locust_master'
    )

    master_task = ecs.describe_tasks(cluster='Fargate_Load_Test_Cluster', tasks=task['taskArns'])['tasks'][0]

    master_ip = _get_master_private_ip(master_task['attachments'][0])
    task_definition_arn = master_task['taskDefinitionArn']

    response = ecs.run_task(
        cluster='Fargate_Load_Test_Cluster',
        launchType='FARGATE',
        networkConfiguration={
            'awsvpcConfiguration': {
                'subnets': ["(서브넷 ID)", "(서브넷 ID)", "(서브넷 ID)"],
                'securityGroups': ["(보안그룹 ID)"],
                'assignPublicIp': 'ENABLED'
            }
        },
        overrides={
            'containerOverrides': [{
                'name': 'LOCUST',
                'environment': [
                    {'name': 'LOCUST_MODE', 'value': 'worker'},
                    {'name': 'LOCUST_MASTER_HOST', 'value': master_ip}
                ]
            }]
        },
        taskDefinition=task_definition_arn,
        count=count
    )

    print('Creating worker tasks finished')
    print('----------------------------')
    for task in response['tasks']:
        print('taskArn:', task['taskArn'])


def _get_eni_id(attachment_details: dict):
    for detail in attachment_details:
        if detail['name'] == 'networkInterfaceId':
            return detail['value']


def get_master_public_ip():
    """ Get public IP address of master service. """
    print('Public IP Address of Master Service -------')
    ecs = boto3.client('ecs')

    tasks_list = ecs.list_tasks(
        cluster='Fargate_Load_Test_Cluster',
        family='LOCUST'
    )

    tasks = ecs.describe_tasks(
        cluster='Fargate_Load_Test_Cluster',
        tasks=tasks_list['taskArns']
    )

    for task in tasks['tasks']:
        if 'startedBy' in task.keys():
            ec2 = boto3.resource('ec2')
            network_interface = ec2.NetworkInterface(_get_eni_id(task['attachments'][0]['details']))
            print(network_interface.association_attribute.PublicIp)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--start', type=int, help='Start worker tasks with the count to run')
    parser.add_argument('--exit', action='store_true', help='End worker tasks')
    parser.add_argument('--get-master-address', action='store_true', help='Get public ip address of master service')

    args = parser.parse_args()

    if args.start is not None:
        start_worker_tasks(args.start)
    elif args.exit is True:
        stop_worker_tasks()
    elif args.get_master_address is True:
        get_master_public_ip()
    else:
        parser.print_help()
