# -*- coding: utf-8 -*-

import requests
from requests.exceptions import ConnectionError, Timeout
from util import parse_timestamp, datetime_to_unix_epoch
import logging
import six
import util


def fetch_objects():
    log = logging.getLogger("geofencebroker")
    try:
        url = "https://www.vegvesen.no/nvdb/api/v2/vegobjekter/911?inkluder=lokasjon,egenskaper,metadata"
        req = requests.get(url, timeout=2.0)

        if not req.ok:
            log.warn("Unable to retrieve NVDB goefence objects")
            return None
        return req.json()
    except (ConnectionError, Timeout) as ce:
        log.error(ce)
        return None


def get_polygon(vegobjekt):
    """
    Input is a "vegobjekt" dictionary from NVDB. Then we'll
    extract the POLYGON datatype and convert it a 2-dimensional
    list of UTM coordinates.
    """
    log = logging.getLogger("geofencebroker")
    tmp = [x for x in vegobjekt["egenskaper"] if x["datatype"] == 19]
    if not tmp:
        log.error("Unable to get POLYGON from vegobjekt!\n\tvegobjekt['egenskaper'] = {}".format(
            vegobjekt["egenskaper"]))
        return []

    # tmp = tmp[0]
    # polygon = tmp["verdi"].replace("POLYGON ((", "").replace("))", "")
    # polygon = [x.strip().split(" ") for x in polygon.split(",")]

    # return polygon
    nvdb_polygon = tmp[0]['verdi']
    return util.parse_polygon(nvdb_polygon)


def get_name(vegobjekt):
    """Return the navn (id=11212) and beskrivelse (id=11213)
    navn = "Oslo Ring 1"
    beskrivelse = "Tester ring 1"
    <- "Oslo Ring 1 (Tester ring 1)"
    """
    name = filter(lambda x: x['id'] == 11212, vegobjekt["egenskaper"])
    description = filter(lambda x: x['id'] == 11213, vegobjekt["egenskaper"])

    return u"{} ({})".format(unicode(name[0]["verdi"]), unicode(description[0]["verdi"]))


def get_version(vegobjekt):
    """Version id field in NVDB has 'id' == 11214"""

    # timestamp = parse_timestamp(vegobjekt["metadata"]["sist_modifisert"])
    # unix_epoch = datetime_to_unix_epoch(timestamp)
    version = filter(lambda x: x["id"] == 11214, vegobjekt["egenskaper"])
    if not version:
        return version

    version = version[0]
    return int(version['verdi'])


def get_polygon_centroid(polygon_input):
    """
    ref https://stackoverflow.com/questions/2792443/finding-the-centroid-of-a-polygon    
    """
    log = logging.getLogger("geofencebroker")


    # Convert the 2D list of string UTM coordinates
    # to proper float numbers. Need for the calculation
    # of the polygon centroid.
    polygon = polygon_input
    if isinstance(polygon_input[0][0], six.string_types):
        polygon = [[float(i) for i in p] for p in polygon_input]

    centroid = [0.0, 0.0]
    signed_area = 0.0
    a = 0.0
    p_length = len(polygon) - 1

    for i in range(p_length):
        x0, y0 = polygon[i][0], polygon[i][1]
        x1, y1 = polygon[i + 1][0], polygon[i + 1][1]

        a = x0 * y1 - x1 * y0
        signed_area += a
        centroid[0] += (x0 + x1) * a
        centroid[1] += (y0 + y1) * a

    x0, y0 = polygon[p_length][0], polygon[p_length][1]
    x1, y1 = polygon[0][0], polygon[0][1]
    a = x0 * y1 - x1 * y0
    signed_area += a
    centroid[0] += (x0 + x1) * a
    centroid[1] += (y0 + y1) * a

    signed_area *= 0.5

    try:
        centroid[0] /= (6.0 * signed_area)
        centroid[1] /= (6.0 * signed_area)
    except ZeroDivisionError:
        log.exception()
        raise
    else:
        return tuple(centroid)

