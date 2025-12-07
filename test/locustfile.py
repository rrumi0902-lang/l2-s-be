import random
import string
import time
from locust import HttpUser, task, between, SequentialTaskSet


def random_string(length=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


class UserScenario(SequentialTaskSet):

    def on_start(self):
        """
        시나리오 시작 전 가입/로그인.
        서버가 죽어있으면(500+) 잠시 쉬었다가 다시 시도하도록 방어 로직 추가.
        """
        self.email = f"{random_string()}@example.com"
        self.password = "testpass123"
        self.username = f"user_{random_string(4)}"

        # 1. 회원가입 (실패 시 대기 로직 추가)
        with self.client.post("/auth/register", json={
            "email": self.email,
            "username": self.username,
            "password": self.password
        }, catch_response=True) as response:
            if response.status_code >= 500:
                print("!! Server Error during Register. Sleeping 10s...")
                time.sleep(10)  # 서버가 살아날 시간을 줌
                response.failure("Server Error")
                self.interrupt()  # 시나리오 중단하고 다시 시작 (on_start 재진입)
                return

        # 2. 로그인
        with self.client.post("/auth/login", json={
            "email": self.email,
            "password": self.password
        }, catch_response=True) as response:
            if response.status_code >= 500:
                print("!! Server Error during Login. Sleeping 10s...")
                time.sleep(10)
                response.failure("Server Error")
                self.interrupt()
                return

    @task
    def browse_dashboard(self):
        # API 호출 시에도 502가 뜨면 즉시 실패 처리되지만,
        # TaskSet 흐름상 wait_time이 있어서 on_start만큼 위험하진 않습니다.
        self.client.get("/health/alive")
        self.client.get("/auth/me")
        self.client.get("/video/my")
        self.client.get("/runpod/job/my")

    @task
    def manage_credit(self):
        self.client.post("/credit/add", json={"amount": 100})

    @task
    def browse_recent_videos(self):
        limit = random.choice([5, 10, 20])
        self.client.get(f"/video/recent?limit={limit}")

    @task
    def cleanup_account(self):
        self.client.delete("/auth/withdraw")
        self.interrupt()


class WebsiteUser(HttpUser):
    tasks = [UserScenario]
    wait_time = between(1, 3)