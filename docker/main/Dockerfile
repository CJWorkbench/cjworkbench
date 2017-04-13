FROM jonathanstray/cjworkbench-reqs
EXPOSE 8000

# start from the repo
RUN git clone --recursive https://github.com/jstray/cjworkbench.git

# python deps already installed, but get node deps
 WORKDIR cjworkbench
RUN npm install

# build assets
RUN ./node_modules/.bin/webpack --config webpack.config.js

# setup db, apply migrations, create initial admin user
RUN python manage.py migrate
RUN python manage.py shell -c "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@cjworkbench.org', 'admin')"

# go! default command runs in debug
CMD python manage.py runserver $(hostname -i):8000
