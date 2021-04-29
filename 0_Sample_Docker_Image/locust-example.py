from locust import HttpUser, TaskSet, task, between


class MyTaskSet(TaskSet):

    @task
    def get_index_page(self):
        self.client.get('/')

    @task
    def get_test_page(self):
        self.client.get('/test.html')


class MyLocust(HttpUser):
    task_set = MyTaskSet
    wait_time = between(5, 15)
