from locust import HttpUser, task, between

class MyTaskSet(HttpUser):
    wait_time = between(5, 15)

    @task
    def get_index_page(self):
        self.client.get('/')

    @task
    def get_test_page(self):
        self.client.get('/test.html')