FROM python:3
EXPOSE 8000

# start from the repo
RUN git clone --recursive https://github.com/jstray/cjworkbench.git

# python deps
RUN cd cjworkbench && \
    pip install -r requirements.txt && \
    pip install -r requirements-dev.txt

# node and npm deps
RUN curl -sL https://deb.nodesource.com/setup_6.x | bash -
RUN apt-get install nodejs
RUN cd cjworkbench && npm install

# build assets
RUN cd cjworkbench && \
    ./node_modules/.bin/webpack --config webpack.config.js

# setup db, apply migrations
RUN cd cjworkbench && \
    python manage.py migrate

# go!
CMD cd cjworkbench && \
    python manage.py runserver

#CMD start redis && \
#    python manage.py runworker && \
#    daphne cjworkbench.asgi:channel_layer
