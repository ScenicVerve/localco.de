# localco.de

A Local Code Web Application for managing and serving GIS data and using the [topology](https://github.com/open-reblock/topology) library to calculate shortest paths connecting aggregated parcels.

Apps that need to be installed for this to work:

* [textbits](https://github.com/bengolder/textbits) (which depends on markdown2)
* [topology](https://github.com/open-reblock/topology)

The app currently uses a [PostGIS](https://postgis.net/) database and requires the [geoDjango](https://ocs.djangoproject.com/en/1.8/ref/contrib/gis/install/) libraries. 

## Installation (Ubuntu 14.04)

```bash
sudo apt-get install python-dev python-virtualenv python-pip postgresql-9.3-postgis-2.1 postgresql-server-dev-9.3 python-numpy python-matplotlib python-scipy
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

Set `my_path` in `settings.py` to the parent directory of your working copy. Create `mysettings.py`.

```bash
echo PW='postgrespass' > pw.py
sudo -u postgres createuser -P localcode
sudo -u postgres createuser -O localcode open_reblock

# (edit /etc/postgresql/9.3/main/pg_hba.conf to change all connections to trust)
sudo /etc/init.d/postgresql restart

sudo -u postgres psql -d open_reblock -c "create extension postgis"

python manage.py syncdb
```

## Starting

```bash
python manage.py runserver 0.0.0.0:8000
```

(N.b. the `0.0.0.0` is to allow connections from hosts other than `localhost`. This is necessary if running in a VM, for example.)

## Troubleshooting

If you see an error like `django.contrib.gis.geos.error.GEOSException: Could not parse version info string "3.4.2-CAPI-1.8.2 r3921"`, you'll need to manually patch `venv/lib/python2.7/site-packages/django/contrib/gis/geos/libgeos.py` per http://stackoverflow.com/questions/18643998/geodjango-geosexception-error
