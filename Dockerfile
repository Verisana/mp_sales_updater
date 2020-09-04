FROM python:3.8-buster

WORKDIR /home/gr1902/mp_sales_updater

# install psycopg2 dependencies
RUN apt-get update && apt-get install -y python3-dev libpq-dev netcat locales

# Locale
RUN sed -i -e \
  's/# ru_RU.UTF-8 UTF-8/ru_RU.UTF-8 UTF-8/' /etc/locale.gen \
   && locale-gen

ENV LANG ru_RU.UTF-8
ENV LANGUAGE ru_RU:ru
ENV LC_LANG ru_RU.UTF-8
ENV LC_ALL ru_RU.UTF-8

# +Timezone
# ENV TZ Europe/Moscow
# RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
RUN mkdir logs && mkdir media && mkdir static
ENTRYPOINT ["/home/gr1902/mp_sales_updater/.docker/entrypoint.sh"]