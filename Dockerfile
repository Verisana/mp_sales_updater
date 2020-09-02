FROM python:3.8-buster

WORKDIR /home/gr1902/mp_sales_updater

# install psycopg2 dependencies
RUN apt-get update && apt-get install -y python3-dev libpq-dev netcat

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
RUN mkdir logs && mkdir media && mkdir static
ENTRYPOINT ["/home/gr1902/mp_sales_updater/.docker/entrypoint.sh"]