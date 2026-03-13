FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY vendor ./vendor
COPY tests ./tests
COPY main.py ./main.py
EXPOSE 8080
ENTRYPOINT ["python3", "main.py"]
