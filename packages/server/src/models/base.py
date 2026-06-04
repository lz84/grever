from sqlalchemy.orm import declarative_base

Base = declarative_base()

# 注：auth/models.py 使用自己的 Base，避免循环依赖
