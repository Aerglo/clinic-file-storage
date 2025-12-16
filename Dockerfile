FROM python:3.10-slim

# جلوگیری از ساخت فایل‌های کش پایتون (pyc)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# تنظیم دایرکتوری کاری
WORKDIR /app

# نصب پیش‌نیازهای پستگرس
RUN apt-get update && apt-get install -y libpq-dev gcc

# کپی کردن نیازمندی‌ها و نصب
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install gunicorn psycopg2-binary

# کپی کردن کل پروژه
COPY . /app/