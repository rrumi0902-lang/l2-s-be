from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool  # 1. NullPool 임포트 추가
from app.config.environments import SUPABASE_DB_URL

# psycopg2 주소를 asyncpg로 변환
ASYNC_DB_URL = SUPABASE_DB_URL.replace("postgresql+psycopg2", "postgresql+asyncpg")

# Vercel(서버리스) 최적화 설정
engine = create_async_engine(
    ASYNC_DB_URL,
    poolclass=NullPool,  # 2. 풀링을 끄고 즉시 연결/해제로 변경 (가장 중요)
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
)

AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()