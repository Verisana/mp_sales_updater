FROM python:3.8-buster

RUN useradd --create-home gr1902 && chown -R gr1902 /home/gr1902/
WORKDIR /home/gr1902/mp_sales_updater

# install psycopg2 dependencies
RUN apt-get update && apt-get install -y python3-dev libpq-dev netcat

USER gr1902

ENV VIRTUAL_ENV=/home/gr1902/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY --chown=gr1902 ./requirements.txt .
RUN /home/gr1902/venv/bin/python3 -m pip install --upgrade pip
RUN pip install wheel==0.34.2
RUN pip install -r requirements.txt

COPY --chown=gr1902 . .
RUN mkdir logs
ENTRYPOINT ["/home/gr1902/mp_sales_updater/entrypoint.sh"]