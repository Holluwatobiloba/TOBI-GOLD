FROM python:3.11-slim 
WORKDIR /app 
COPY requirements.txt . 
RUN python -m pip install --index-url https://pypi.org/simple --prefer-binary --default-timeout=1000 --retries 10 --no-cache-dir -r requirements.txt 
COPY . . 
EXPOSE 8000
