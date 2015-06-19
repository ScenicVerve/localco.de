# localco.de

A Local Code Web Application for managing and serving GIS data and using the [topology](github.com/open-reblock/topology) library to calculate shortest paths connecting aggregated parcels.

Apps that need to be installed for this to work:

* [textbits](github.com/bengolder/textbits) (which depends on markdown2)
* [topology](github.com/open-reblock/topology)

The app currently uses a [PostGIS](postgis.net/) database and requires the [geoDjango](docs.djangoproject.com/en/1.8/ref/contrib/gis/install/) libraries. 
