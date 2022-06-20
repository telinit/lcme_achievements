# syntax=docker/dockerfile:1
FROM python:3
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apt update -y && apt install libreoffice-nogui -y
COPY ./fonts/lato2 /usr/share/fonts/
RUN fc-cache --force --verbose
WORKDIR /code
COPY . /code
RUN chmod +x /code/*.sh
RUN pip install -r requirements.txt

