from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config.environments import SUPABASE_DB_URL
from sqlalchemy.pool import QueuePool

engine = create_engine(SUPABASE_DB_URL,
                       pool_pre_ping=True,
                       poolclass=QueuePool,
                       pool_size=5,
                       max_overflow=10,
                       pool_timeout=30,
                       pool_recycle=3600)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()