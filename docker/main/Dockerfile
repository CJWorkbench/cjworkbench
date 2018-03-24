FROM cjworkbench/cjworkbench-requirements
EXPOSE 8000

# start from the repo. print last commit to docker build log
RUN git clone https://github.com/CJWorkbench/cjworkbench.git
WORKDIR cjworkbench
RUN git checkout stable
RUN git status
RUN git log -1

# python deps already installed, but get node deps
RUN npm install

# build assets
RUN ./node_modules/.bin/webpack -p --config webpack.config.js

# seriously, get an editor in there for debugging
RUN apt-get install nano

# setup db, apply migrations.
# Need sites migration to create django_sites table, so later (normal) migration can set site URL
RUN python manage.py migrate sites
RUN python manage.py migrate

# setup cron job for every minute to do scheduled checks for new data
RUN echo "* * * * * /usr/bin/curl http://localhost:8000/runcron" | crontab

# You'd think this would work, but no. For some reason never. Had to put it in start-prod.sh
# RUN cron

# go! default command runs in debug. docker-compose.yml runs start-prod.sh for the real thing
CMD python manage.py runserver $(hostname -i):8000
