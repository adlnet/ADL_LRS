# ADL LRS

## Installiation

    virtualenv --no-site-packages adl_lrs

    . adl_lrs/bin/activate

    git clone https://github.com/adlnet/adl_lrs

    cd adl_lrs

    pip install -r requirements.txt

## Starting

    cd adl_lrs

    supervisord

 To verify it's running

     supervisorctl

 you should see a task named web running


This will host the application using gunicorn with 2 worker processes