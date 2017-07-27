# This is the "requirements" container, jonathanstray/cjworkbench-reqs
# It isolates all of the time-consuming setup of pip requirements (and a few other basics) from app code changes

FROM python:3
EXPOSE 8000

RUN curl https://raw.githubusercontent.com/jstray/cjworkbench/master/requirements.txt > requirements.txt
RUN curl https://raw.githubusercontent.com/jstray/cjworkbench/master/requirements-dev.txt > requirements-dev.txt

RUN pip install -r requirements.txt && \
    pip install -r requirements-dev.txt

# node and npm deps
RUN curl -sL https://deb.nodesource.com/setup_6.x | bash -
RUN apt-get install nodejs

# Seriously, this ships without cron?
RUN apt-get install cron
