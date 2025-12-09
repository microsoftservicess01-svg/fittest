
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py ./
COPY brands.json ./
ENV FLASK_ENV=production
EXPOSE 5000
CMD ["gunicorn","-w","3","-b","0.0.0.0:5000","app:app"]
