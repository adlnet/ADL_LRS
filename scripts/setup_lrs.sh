./manage.py createcachetable
./manage.py migrate
./manage.py makemigrations adl_lrs lrs oauth_provider
./manage.py migrate
#./manage.py createsuperuser
./manage.py runserver 0.0.0.0:8000