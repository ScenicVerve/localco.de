# localco.de

A Local Code Web Application for managing and serving GIS data and using the [topology](https://github.com/open-reblock/topology) library to calculate shortest paths connecting aggregated parcels.

Apps that need to be installed for this to work:

* [textbits](https://github.com/bengolder/textbits) (which depends on markdown2)
* [topology](https://github.com/open-reblock/topology)

The app currently uses a [PostGIS](https://postgis.net/) database and requires the [geoDjango](https://ocs.djangoproject.com/en/1.8/ref/contrib/gis/install/) libraries. 

## Installation (Ubuntu 14.04)
username is reblock
```bash
sudo apt-get install python-dev python-virtualenv python-pip postgresql-9.3-postgis-2.1 postgresql-server-dev-9.3 python-numpy python-scipy
sudo apt-get install git
git clone https://github.com/open-reblock/localco.de.git localcode
cd localcode
virtualenv --system-site-packages venv
. venv/bin/activate
sudo apt-get install aptitude
sudo aptitude install libblas-dev liblapack-dev
sudo apt-get install libatlas-base-dev gfortran

pip install -r requirements.txt
sudo apt-get install rabbitmq-server

git clone https://github.com/bengolder/textbits
git clone https://github.com/open-reblock/topology

```

## Installation (RedHat 6.08)

```bash
sudo yum install python-virtualenv python-pip python-numpy python-matplotlib python-scipy
sudo rpm -ivh http://yum.postgresql.org/9.3/redhat/rhel-6-x86_64/pgdg-redhat93-9.3-1.noarch.rpm
yum install postgresql93 postgresql93-server postgresql93-libs postgresql93-contrib postgresql93-devel
sudo yum install postgis2_93
yum install pgrouting_93
git clone https://github.com/open-reblock/localco.de localcode
cd localcode
virtualenv --system-site-packages venv
. venv/bin/activate
pip install -r requirements.txt
git clone https://github.com/bengolder/textbits
git clone https://github.com/open-reblock/topology

pip install networkx pyshp plotly
```

## Configuration

Set `my_path` in `settings.py` to the parent directory of your working copy. Use the `mysettings.py`template, change the MEDIA_ROOT according to the username(reblock)



```bash

echo PW='postgrespass' > pw.py
sudo -u postgres createuser --superuser $USER
sudo -u postgres psql
postgres=# \password $USER
psql
create database open_reblock;

# (edit /etc/postgresql/9.3/main/pg_hba.conf to change all connections to trust)
sudo /etc/init.d/postgresql restart

sudo -u postgres psql -d open_reblock -c "create extension postgis"

python manage.py syncdb
```

## Starting

```bash
Django:
python manage.py runserver 0.0.0.0:8000

Celery:
python manage.py celery -A tasks worker --loglevel=info
```

(N.b. the `0.0.0.0` is to allow connections from hosts other than `localhost`. This is necessary if running in a VM, for example.)

## Troubleshooting

If you see an error like `django.contrib.gis.geos.error.GEOSException: Could not parse version info string "3.4.2-CAPI-1.8.2 r3921"`, you'll need to manually patch `venv/lib/python2.7/site-packages/django/contrib/gis/geos/libgeos.py` per http://stackoverflow.com/questions/18643998/geodjango-geosexception-error

## Deploying to the server
The server is running `RedHat6.08`. RedHat6 is running `Python 2.6.6`. The app and libraries were not installed on a `virtualenv`, so we are running `Python 2.6` instead of `Python 2.7`.
