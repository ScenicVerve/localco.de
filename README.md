# localco.de

A Local Code Web Application for managing and serving GIS data and using the [topology](https://github.com/open-reblock/topology) library to calculate shortest paths connecting aggregated parcels.

Apps that need to be installed for this to work:

* [textbits](https://github.com/bengolder/textbits) (which depends on markdown2)
* [topology](https://github.com/open-reblock/topology)

The app currently uses a [PostGIS](https://postgis.net/) database and requires the [geoDjango](https://ocs.djangoproject.com/en/1.8/ref/contrib/gis/install/) libraries. 
