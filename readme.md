# ADL LRS 

#### Installation tested on Ubuntu 12.10 machine with Python 2.7.3. Should be good with Ubuntu 10.04 LTS - 13.04 releases. Updated to be compliant with the 1.0.1 xAPI spec.

This version is stable, but only intended to support a small amount of users as a proof of concept. While it uses programming best practices, it is not designed to take the place of an enterprise system.

## Quick Installation

(Optional) Prior to cloning the repository, create an ADL LRS system user and switch to that user:

```
sudo su

useradd -c "ADL Learning Record Store System" -m -s "/bin/bash" adllrs

su adllrs

cd ~
```

change to root and run setup_lrs.sh:

```
sudo su
./setup_lrs.sh
```

For development, you can run the LRS with:

```
python manage.py runserver
```

Alternatively, follow the instructions below.

## Starting

While still in the ADL_LRS directory, run

    (env)dbowner:ADL_LRS$ supervisord

To verify it's running

    (env)dbowner:ADL_LRS$ supervisorctl

Set your site domain

  Visit the admin section of your website (/admin). Click Sites and you'll see the only entry is 'example.com' (The key for this in the DB is 1 and it maps back to the SITE_ID value in settings). Change the domain and name to the domain you're going to use. If running locally it could be localhost:8000, or if production could be lrs.adlnet.gov (DON'T include the scheme here, that should be set in settings.py already). Sync your database again to apply the change

    (env)dbowner:ADL_LRS$ python manage.py syncdb



Whenever you want to exit the virtual environment, just type `deactivate`

You should see a task named web running. This will host the application using gunicorn with 2 worker processes.
If you open a browser and visit http://localhost:8000/xapi you will hit the LRS. Gunicorn does not serve static files
so no CSS will be present. This is fine if you're doing testing/development but if you want to host a production-ready
LRS, Nginx needs to be setup to serve static files. For more production-like environments, we also recommend using uWSGI instead of Gunicorn. Please read [these](https://github.com/adlnet/ADL_LRS/wiki/Using-Nginx-for-Production) instructions for including
Nginx and using uWSGI intead of Gunicorn. For a more detailed description of the tools being used in general, visit [here](https://github.com/adlnet/ADL_LRS/wiki/Putting-the-Pieces-Together). Additionally if you're just doing dev, instead of using supervisor you can just run `python manage.py runserver` and use Django's built-in web server.

## Test LRS
    
    (env)dbowner:ADL_LRS$ fab test_lrs

## Helpful Information
    
* [Test Coverage](https://github.com/adlnet/ADL_LRS/wiki/Code-Coverage)
* [Code Profiling](https://github.com/adlnet/ADL_LRS/wiki/Code-Profiling-with-cProfile)
* [Sending Attachments](https://github.com/adlnet/ADL_LRS/wiki/Sending-Statements-with-Attachments)
* [Setting up Nginx and uWSGI](https://github.com/adlnet/ADL_LRS/wiki/Using-Nginx-for-Production)
* [OAuth Help](https://github.com/adlnet/ADL_LRS/wiki/Using-OAuth)
* [Clearing the Database](https://github.com/adlnet/ADL_LRS/wiki/Clearing-the-Database)

## License
   Copyright &copy;2015 Advanced Distributed Learning

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
