FROM jonathanstray/cjworkbench-reqs
EXPOSE 8000

# start from the repo
RUN git clone --recursive https://github.com/jstray/cjworkbench.git

# python deps already installed, but get node deps
WORKDIR cjworkbench
RUN npm install

# build assets
RUN ./node_modules/.bin/webpack -p --config webpack.config.js

# setup db, apply migrations
RUN python manage.py migrate

# go! default command runs in debug
CMD python manage.py runserver $(hostname -i):8000
