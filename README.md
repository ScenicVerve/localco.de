# localco.de

A Local Code Web Application for managing and serving GIS data and using the [topology](https://github.com/open-reblock/topology) library to calculate shortest paths connecting aggregated parcels.

Apps that need to be installed for this to work:

* [textbits](https://github.com/bengolder/textbits) (which depends on markdown2)
* [topology](https://github.com/open-reblock/topology)

The app currently uses a [PostGIS](https://postgis.net/) database and requires the [geoDjango](https://ocs.djangoproject.com/en/1.8/ref/contrib/gis/install/) libraries. 

## Installation (Ubuntu 14.04)

```bash
sudo apt-get install python-dev python-virtualenv python-pip postgresql-9.3-postgis-2.1 postgresql-server-dev-9.3
git clone https://github.com/open-reblock/localco.de localcode
cd localcode
virtualenv venv
. venv/bin/activate
pip install -r requirements.txt
git clone https://github.com/bengolder/textbits
git clone https://github.com/open-reblock/topology
```

## Configuration

Set `my_path` in `settings.py` to the parent directory of your working copy. Create `mysettings.py`.

```bash
echo PW='postgrespass' > pw.py
```

## Starting

```bash
python manage.py runserver
```
