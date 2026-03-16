# 使用官方 Python 镜像
FROM python:3.11-slim

# 安装系统依赖（Chromium 和相关库）
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p data log

# 暴露端口
EXPOSE 8501

# 设置环境变量
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 设置默认端口（Railway 会通过环境变量覆盖）
ENV PORT=8501

# 启动命令
CMD streamlit run src/app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
