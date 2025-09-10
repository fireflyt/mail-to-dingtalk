# 第一阶段：构建环境
FROM python:3.12.11-slim-bullseye as builder

# 设置工作目录
WORKDIR /app

# 使用阿里云源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# 安装必要的构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 设置阿里云PyPI镜像并安装Python依赖
RUN pip install --no-cache-dir \
    -i https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com \
    --prefix=/install \
    requests==2.31.0 \
    html2text==2020.1.16

# 第二阶段：运行环境
FROM python:3.12.11-slim-bullseye

# 安装procps包以获取ps命令
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends procps && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 从构建阶段复制已安装的包
COPY --from=builder /install /usr/local

# 复制应用程序文件
COPY email_monitor.py /app/

# 创建日志目录
RUN mkdir -p /app/logs && chmod 777 /app/logs

# 设置时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo 'Asia/Shanghai' >/etc/timezone

# 设置环境变量（可以在运行时覆盖）
ENV IMAP_HOST="imap.exmail.qq.com"
ENV EMAIL_USER=""
ENV EMAIL_PASS=""
ENV SENDER_FILTER=""
ENV DING_WEBHOOK=""
ENV DING_SECRET=""
ENV CHECK_INTERVAL=10
ENV LOG_LEVEL="INFO"

# 设置容器健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD bash -c "ps -ef | grep '[p]ython email_monitor.py' || exit 1"

# 设置容器入口点
ENTRYPOINT ["python", "email_monitor.py"]
