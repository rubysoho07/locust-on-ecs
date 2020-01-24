from locust import HttpLocust, TaskSet, task, between


class MyTaskSet(TaskSet):

    @task(2)
    def get_index_page(self):
        self.client.get('/')

    @task(1)
    def get_detail_page(self):
        self.client.get('/musicmanager/album/1/')


class MyLocust(HttpLocust):
    task_set = MyTaskSet
    wait_time = between(5, 15)
