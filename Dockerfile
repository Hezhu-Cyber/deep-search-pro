# Deep Search Pro - 镜像构建
# 多阶段说明：直接运行依赖安装 + 源码拷贝（保持简单、可读）
FROM python:3.11-slim

# WeasyPrint 运行所需系统库（Pango / 字体，含中日韩字体用于中文 PDF）
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        shared-mime-info \
        fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝源码
COPY . .

EXPOSE 8000

# 生产模式：关闭 reload
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]