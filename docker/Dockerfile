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

WORKDIR cjworkbench
RUN cd npm install

# build assets
RUN ./node_modules/.bin/webpack --config webpack.config.js

# setup db, apply migrations, create initial admin user
RUN python manage.py migrate
RUN python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@cjworkbench.org', 'admin')"

# go!
CMD python manage.py runserver $(hostname -i):8000
