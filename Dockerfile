# 1. استفاده از پایتون سبک
FROM python:3.11-slim

# 2. جلوگیری از ساخت فایل‌های اضافی پایتون
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. ساخت پوشه کاری داخل داکر
WORKDIR /app

# 4. نصب وابستگی‌های سیستم (برای پستگرس و ...)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. کپی کردن لیست پکیج‌ها و نصبشون
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 6. کپی کردن کل پروژه به داخل داکر
COPY . /app/

# 7. دستور اجرای برنامه (با پورت 8000)
# به جای "my_project_name" اسم پوشه‌ای که settings.py توشه رو بنویس
CMD ["gunicorn", "my_project_name.wsgi:application", "--bind", "0.0.0.0:8000"]