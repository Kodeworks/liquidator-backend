FROM python:3.7-slim

ENV PYTHONUNBUFFERED 1

RUN useradd django -u 1000 -U -s /bin/false

WORKDIR /code

COPY requirements.txt /code/

RUN pip install -r /code/requirements.txt

COPY . /code/

USER django
