FROM python:3.11-slim
"
        "WORKDIR /workspace
"
        "COPY requirements.txt /workspace/requirements.txt
"
        "RUN pip install --no-cache-dir -r /workspace/requirements.txt
"
        "COPY . /workspace
"
        "ENV PYTHONUNBUFFERED=1
"
        "CMD ["bash", "artifacts/router_camera_ready_v1/reproduce_main_tables_figures.sh"]
"
        