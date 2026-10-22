# colour-demo 服务端镜像：一条 uvicorn 命令托管 API + 静态原型（方案 G3 零前端构建）
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # 出图只走无头后端；服务端禁用 bbox_inches="tight"（方案 10.4）
    MPLBACKEND=Agg \
    # matplotlib 字体缓存目录必须可写，否则首次导入极慢（包内 __init__ 也会兜底设一次）
    MPLCONFIGDIR=/tmp/colour-demo-mpl

WORKDIR /app

# colour-science 版本由 pyproject 锁死（==0.4.7），这里不再重复写版本号
COPY pyproject.toml README.md ./
COPY src ./src

# 用可编辑安装：main.py 用 __file__ 的 parents[2] 定位 docs/prototype，
# 只有源码树留在 /app 才能把静态原型挂在 /demo 上（换 site-packages 会静默丢挂载）。
# 不用 BuildKit 的 cache mount：经典构建器也能构建（本机就没有 buildx）
RUN pip install --no-cache-dir -e .

# 静态单页原型（构建期已生成，398 KB 单文件）
COPY docs/prototype ./docs/prototype

# 非 root 运行；/tmp 下的 mpl 缓存在启动时才创建，权限够用
RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "colour_demo.main:app", "--host", "0.0.0.0", "--port", "8000"]
