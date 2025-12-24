from fastapi.middleware.cors import CORSMiddleware

def add_cors(application):
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://shortcake-fe.vercel.app",
            "https://shortcake-lqavsdtie-melaka.vercel.app" # 에러에 뜬 미리보기 주소도 추가
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )