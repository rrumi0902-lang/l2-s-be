import subprocess

if __name__ == "__main__":
    cmd = [
        "locust",
        "-f", "test/locustfile.py",
        "--host", "https://l2s-be.journey-planner.org",
        "--loglevel", "INFO"
    ]

    # stdout, stderr 인자를 제거하여 터미널에 바로 출력되게 함
    process = subprocess.Popen(cmd)

    process.wait()  # 프로세스가 끝날 때까지 대기