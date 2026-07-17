FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

WORKDIR /app

# 安装系统依赖（pandas 需要）
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装所有 Python 依赖
RUN pip install --no-cache-dir \
    fastapi>=0.115 \
    uvicorn[standard]>=0.32 \
    sqlalchemy>=2.0 \
    psycopg2-binary>=2.9 \
    pandas>=2.0 \
    openpyxl>=3.0 \
    numpy>=1.24 \
    python-multipart \
    pydantic-settings

COPY app ./app

RUN mkdir -p /app/data/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]