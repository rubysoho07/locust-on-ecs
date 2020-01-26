from locust import HttpLocust, TaskSet, task, between


class MyTaskSet(TaskSet):

    @task
    def get_index_page(self):
        self.client.get('/')


class MyLocust(HttpLocust):
    task_set = MyTaskSet
    wait_time = between(5, 15)
