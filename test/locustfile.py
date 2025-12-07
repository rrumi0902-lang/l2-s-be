import random
import string
from locust import HttpUser, task, between, SequentialTaskSet


def random_string(length=8):
    """랜덤 문자열 생성 (아이디/비번용)"""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


class UserScenario(SequentialTaskSet):
    """
    가입 -> 활동(조회/충전) -> 탈퇴 시나리오
    영상 업로드 같은 무거운 작업은 제외하고 부하가 적은 조회 위주로 구성됨
    """

    def on_start(self):
        """1. 회원가입 및 로그인"""
        self.email = f"{random_string()}@example.com"
        self.password = "testpass123"
        self.username = f"user_{random_string(4)}"

        # 회원가입
        self.client.post("/auth/register", json={
            "email": self.email,
            "username": self.username,
            "password": self.password
        })

        # 로그인 (쿠키 자동 저장)
        self.client.post("/auth/login", json={
            "email": self.email,
            "password": self.password
        })

    @task
    def browse_dashboard(self):
        """2. 대시보드 진입 시 발생하는 조회 요청들"""
        # 서버 상태 및 내 정보 확인
        self.client.get("/health/alive")
        self.client.get("/auth/me")

        # 내 비디오 목록 확인 (업로드를 안 했으므로 빈 목록 예상)
        self.client.get("/video/my")

        # 내 작업 목록 확인
        self.client.get("/runpod/job/my")

    @task
    def manage_credit(self):
        """3. 크레딧 충전 테스트 (가벼운 트랜잭션)"""
        # 크레딧 충전
        self.client.post("/credit/add", json={"amount": 100})

    @task
    def browse_recent_videos(self):
        """4. 최신 영상 목록 조회 (메인 기능 테스트)"""
        # 최근 완료된 영상 목록 조회 (limit 파라미터 랜덤 변경)
        limit = random.choice([5, 10, 20])
        self.client.get(f"/video/recent?limit={limit}")

    @task
    def cleanup_account(self):
        """5. 시나리오 종료: 회원 탈퇴로 DB 정리"""
        # 회원 탈퇴 (DB에서 유저 및 세션 삭제)
        self.client.delete("/auth/withdraw")

        # 시나리오 종료
        self.interrupt()


class WebsiteUser(HttpUser):
    tasks = [UserScenario]
    # 실제 유저처럼 각 행동 사이에 1~3초 대기
    wait_time = between(1, 3)