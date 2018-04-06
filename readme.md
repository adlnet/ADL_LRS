# ADL LRS

## Jump To:
*	[Installation (Linux)](./readme.md#installation-linux) 
* 	[Installation (Windows)](./readme.md#installation-windows)

#### Installation tested on <b>Ubuntu 14.04</b> machine with Python 2.7.6, <b>Ubuntu 14.04+</b> is recommended. Updated to be compliant with the 1.0.3 xAPI spec.

This version is stable, but only intended to support a small amount of users as a proof of concept. While it uses programming best practices, it is not designed to take the place of an enterprise system.

## [Installation (Linux)](#installation-linux)

**Install Postgres** (The apt-get upgrade is only needed if you're running Ubuntu 14. If running 15+ you can skip to installing postgresql. Also version 9.4+ is needed)

    admin:~$ wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
    admin:~$ sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" >> /etc/apt/sources.list.d/postgresql.list'
    admin:~$ sudo apt-get update
    admin:~$ sudo apt-get upgrade

    admin:~$ sudo apt-get install postgresql-9.4 postgresql-server-dev-9.4 postgresql-contrib-9.4
    (can install 9.5 if on Ubuntu 16)

    admin:~$ sudo -u postgres createuser -P -s <db_owner_name>
    Enter password for new role: <db_owner_password>
    Enter it again: <db_owner_password>
    admin:~$ sudo -u postgres psql template1
    template1=# CREATE DATABASE lrs OWNER <db_owner_name>;
    template1=# \q (exits shell)


**Install Prerequisites**

    admin:~$ sudo apt-get install git fabric python-setuptools python-dev\
        libxml2-dev libxslt1-dev gcc
    admin:~$ sudo easy_install pip
    admin:~$ sudo pip install virtualenv

**Clone the LRS repository**

    admin:~$ cd <wherever you want to put the LRS>
    admin:~$ git clone https://github.com/adlnet/ADL_LRS.git
    admin:~$ cd ADL_LRS/

**Set the LRS configuration**

  Create a `settings.ini` file and place it in the `adl_lrs` directory. Visit the [Settings](https://github.com/adlnet/ADL_LRS/wiki/Settings) wiki page to set it up.


**Setup the environment**

    admin:ADL_LRS$ fab setup_env
    admin:ADL_LRS$ source ../env/bin/activate
    (env)admin:ADL_LRS$


**Setup the LRS**

This creates the top level folders, <b>logs</b> and <b>media</b> at the same level as the project folder, <b>ADL_LRS</b>. Throughout the readme and the other install guides for celery and nginx you will most likely want to direct any log files to the logs directory. Inside of <b>logs</b> there are directorys for <b>celery</b>, <b>supervisord</b>, <b>uwsgi</b> and <b>nginx</b>.

    (env)admin:ADL_LRS$ fab setup_lrs
    ...
    You just installed Django's auth system, which means you don't have any superusers defined.
    Would you like to create one now? (yes/no): yes
    Username (leave blank to use '<system_user_name>'):
    E-mail address:
    Password: <this can be different than your system password since this will just be for the LRS site>
    Password (again):
    Superuser created successfully.
  ...

If you get some sort of authentication error here, make sure that Django and PostgreSQL are both
using the same form of authentication (*adl_lrs/settings.py* and *pg_hba.conf*) and that the credentials
given in *settings.py* are the same as those you created.

<b>IMPORTANT:</b> You <b>MUST</b> setup celery for retrieving the activity metadata from the ID as well as voiding statements that might have come in out of order. Visit the [Using Celery](https://github.com/adlnet/ADL_LRS/wiki/Using-Celery) wiki page for installation instructions.

## [Installation (Windows)](#installation-windows)

#### Installation tested Windows  7 and 8.1.  If you encounter issues, please post an Issue with your problems.

**Install Postgres 9.6**  You can [download an installer here](https://www.openscg.com/bigsql/postgresql/installers.jsp/).

Once that's finished installing, open a command window and navigate to where it was installed (*C:\PostgreSQL* by default).  If you chose a different path, replace the default path below with your own.

```
    > cd c:\postgresql\pg96\bin
    c:\postgresql\pg96\bin> createuser -U postgres -P -s <db_owner_name>

    Enter password for new role: <db_owner_password>
    Enter it again: <db_owner_password>

    c:\postgresql\pg96\bin> psql -U postgres template1

    template1=# CREATE DATABASE lrs OWNER <db_owner_name>;
    template1=# \q (exits shell)
```

**Be sure you include the semicolon on your `CREATE DATABASE` statement**.  

**Install Python**  

This project uses [Python 2](https://www.python.org/downloads/)

**Install Prerequisites**

Assuming you did not add Python2 to your system's PATH variable, navigate to it with a command window (*C:\Python27* by default, but may be different depending on your version of Python).
    
    > cd c:\python27\scripts
    c:\python27\scripts> easy_install pip
    c:\python27\scripts> pip install virtualenv
    c:\python27\scripts> pip install fabric

**Clone the LRS repository**

    > cd <wherever you want to put the LRS>
    > git clone https://github.com/adlnet/ADL_LRS.git
    > cd ADL_LRS/

**Set the LRS configuration**

Create a `settings.ini` file and place it in the `adl_lrs` directory. Visit the [Settings](https://github.com/adlnet/ADL_LRS/wiki/Settings) wiki page to set it up.

## Windows-Specific Modifications

There are a few required changes to the setup processes to run the LRS on Windows.

**Replace Requirements.txt**

A `pyinotify` and `pycrypto` cannot be installed on windows.  You will need to replace the contents of `requirements.txt` with the following: 

```
Django==1.9.1
amqp==1.4.9
bencode==1.0
celery==3.1.19
django-cors-headers==1.1.0
django-jsonify==0.3.0
importlib==1.0.3
isodate==0.5.4
oauth2==1.9.0.post1
pycryptodome==3.4.11
psycopg2==2.6.1
python-jose==2.0.2
pytz==2015.7
requests==2.9.1
rfc3987==1.3.4
supervisor==3.2.0
```

Once this is done, install these libraries using `pip`.  Assuming you did not add Python to your path, you will need to supply a path to pip on your system.  The default path is shown below:

```
ADL_LRS> c:\python27\scripts\pip install -r requirements.txt
```

**Modify Fabfile.py**

Change the `setup_env` function:
```
def setup_env():
    INSTALL_STEPS = [
        'c:\\python27\\scripts\\virtualenv env', 
		'env\\scripts\\activate',
		'env\\scripts\\pip install -r requirements.txt',
		'env\\scripts\\deactivate']
    for step in INSTALL_STEPS:
        local(step)
```

Change the environment directory path in the `setup_lrs` function:
```
    env_dir = os.path.join(cwd, 'env/lib/site-packages')
    if env_dir not in sys.path:
        sys.path.append(env_dir)
```

Change the bottom of the `setup_lrs` function:
```
    # Create cache tables and sync the db
    local('env\\scripts\\python manage.py createcachetable')
    local('env\\scripts\\python manage.py migrate')
    local('env\\scripts\\python manage.py makemigrations adl_lrs lrs oauth_provider')
    local('env\\scripts\\python manage.py migrate')
    local('env\\scripts\\python manage.py createsuperuser')
```

Change the `test_lrs` function:
```
def test_lrs():
    local('env\\scripts\\python manage.py test lrs.tests')
```

Once those are finished, run these from the ADL_LRS directory:
```
    ADL_LRS> c:\python27\scripts\fab setup_env
    ADL_LRS> env\scripts\activate
    (env) ADL_LRS>
```

**Setup the LRS**

Assuming you do not have Python2 on your system path, navigate to the ADL_LRS folder and use the following:

    (env) ADL_LRS> c:\python27\scripts\fab setup_lrs
    ...
    You just installed Django's auth system, which means you don't have any superusers defined.
    Would you like to create one now? (yes/no): yes
    Username (leave blank to use '<system_user_name>'):
    E-mail address:
    Password: <this can be different than your system password since this will just be for the LRS site>
    Password (again):
    Superuser created successfully.
  ...

If you get some sort of authentication error here, make sure that Django and PostgreSQL are both
using the same form of authentication (*adl_lrs/settings.py* and *pg_hba.conf*) and that the credentials
given in *settings.py* are the same as those you created.

## Starting

While still in the ADL_LRS directory, run

    (env) ADL_LRS> env\scripts\python manage.py runserver

This starts a lightweight development web server on the local machine. By default, the server runs on port 8000 on the IP address 127.0.0.1. You can pass in an IP address and port number explicitly. This will serve your static files without setting up Nginx but must NOT be used for production purposes. Press `CTRL + C` to stop the server


Set your site domain

  Visit the admin section of your website (/admin). Click Sites and you'll see the only entry is 'example.com' (The key for this in the DB is 1 and it maps back to the SITE_ID value in settings). Change the domain and name to the domain you're going to use. If running locally it could be localhost:8000, or if production could be lrs.adlnet.gov (DON'T include the scheme here). Once again this does not change the domain it's running on...you want to set that up first then change this value to your domain name.

Whenever you want to exit the virtual environment, just type `deactivate`

For other ways to start and run the LRS, please visit our Wiki.

## Test LRS

    (env)dbowner:ADL_LRS$ fab test_lrs

## Helpful Information

* [Test Coverage](https://github.com/adlnet/ADL_LRS/wiki/Code-Coverage)
* [Code Profiling](https://github.com/adlnet/ADL_LRS/wiki/Code-Profiling-with-cProfile)
* [Setting up Nginx and uWSGI](https://github.com/adlnet/ADL_LRS/wiki/Using-uWSGI-with-Nginx)
* [OAuth Help](https://github.com/adlnet/ADL_LRS/wiki/Using-OAuth)
* [Clearing the Database](https://github.com/adlnet/ADL_LRS/wiki/Clearing-the-Database)

## Contributing to the project
We welcome contributions to this project. Fork this repository, make changes, and submit pull requests. If you're not comfortable with editing the code, please [submit an issue](https://github.com/adlnet/ADL_LRS/issues) and we'll be happy to address it.

## License
   Copyright &copy;2016 Advanced Distributed Learning

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
