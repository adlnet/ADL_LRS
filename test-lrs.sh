#!/bin/bash

cp settings.ini.example adl_lrs/settings.ini
python3 -m unittest discover -s ./lrs/tests -p "test_*.py" -t .
