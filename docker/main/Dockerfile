FROM jonathanstray/cjworkbench-reqs
EXPOSE 8000

# start from the repo
RUN git clone --recursive https://github.com/jstray/cjworkbench.git

# python deps already installed, but get node deps
WORKDIR cjworkbench
RUN npm install

# build assets
RUN ./node_modules/.bin/webpack -p --config webpack.config.js

# setup db, apply migrations.
# Need sites migration to create django_sites table, so later (normal) migration can set site URL
RUN python manage.py migrate sites
RUN python manage.py migrate


# setup cron job for every minute to do scheduled checks for new data
RUN echo "* * * * * /usr/bin/curl http://localhost:8000/runcron" | crontab

# go! default command runs in debug. docker-compose.yml runs start-prod.sh for the real thing
CMD python manage.py runserver $(hostname -i):8000
