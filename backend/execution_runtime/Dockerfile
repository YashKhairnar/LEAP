FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/matplotlib

RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.13.0 \
    numpy==2.3.3 \
    pandas==2.3.2 \
    scikit-learn==1.7.2 \
    matplotlib==3.10.6 \
    seaborn==0.13.2

WORKDIR /workspace
USER 65534:65534
CMD ["python", "/workspace/main.py"]
