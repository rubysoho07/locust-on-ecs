import argparse

import boto3


def stop_slave_tasks():
    """ Stop Slave ECS Tasks """
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

    for detail in attachments['details']:
        if detail['name'] == 'privateIPv4Address':
            return detail['value']


def start_slave_tasks(count: int):
    """ Start Slave ECS Tasks """
    print(f'Start Slave Tasks: {count}')
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
                    {'name': 'LOCUST_MODE', 'value': 'slave'},
                    {'name': 'LOCUST_MASTER_HOST', 'value': master_ip}
                ]
            }]
        },
        taskDefinition=task_definition_arn,
        count=count
    )

    print('Creating slave tasks finished')
    print('----------------------------')
    for task in response['tasks']:
        print('taskArn:', task['taskArn'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--start', type=int, help='Start slave tasks with the count to run')
    parser.add_argument('--exit', action='store_true', help='End slave tasks')

    args = parser.parse_args()

    if args.start is not None:
        start_slave_tasks(args.start)
    elif args.exit is True:
        stop_slave_tasks()
    else:
        parser.print_help()
