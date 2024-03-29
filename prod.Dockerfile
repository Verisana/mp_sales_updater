FROM python:3.8-buster

RUN useradd --create-home gr1902 && chown -R gr1902 /home/gr1902/
WORKDIR /home/gr1902/mp_sales_updater

# install psycopg2 dependencies and other packages
RUN apt-get update && apt-get install -y python3-dev libpq-dev netcat locales nano openssh-server

# Locale
RUN sed -i -e \
  's/# ru_RU.UTF-8 UTF-8/ru_RU.UTF-8 UTF-8/' /etc/locale.gen \
   && locale-gen

ENV LANG ru_RU.UTF-8
ENV LANGUAGE ru_RU:ru
ENV LC_LANG ru_RU.UTF-8
ENV LC_ALL ru_RU.UTF-8

# +Timezone
ENV TZ Asia/Yekaterinburg
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV PYTHONUNBUFFERED 1

COPY --chown=gr1902 ./requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=gr1902 . .
RUN chmod +x .docker/entrypoint.prod.sh && chmod +x .docker/gunicorn_start.sh

USER gr1902

ENTRYPOINT ["/home/gr1902/mp_sales_updater/.docker/entrypoint.prod.sh"]