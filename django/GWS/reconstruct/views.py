import json

import numpy as np
import pygplates
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from utils.model_utils import get_reconstruction_model_dict
from utils.round_float import round_floats


def motion_path(request):
    """
    http GET request to retrieve reconstructed static polygons

    **usage**

    <http-address-to-gws>/reconstruct/motion_path/seedpoints=\ *points*\&timespec=\ *time_list*\&fixplate=\ *fixed_plate_id*\&movplate=\ *moving_plate_id*\&time=\ *reconstruction_time*\&model=\ *reconstruction_model*

    :param seedpoints: integer value for reconstruction anchor plate id [required]

    :param timespec: specification for times for motion path construction, in format 'mintime,maxtime,increment' [defaults to '0,100,10']

    :param time: time for reconstruction [default=0]

    :param fixplate: integer plate id for fixed plate [default=0]

    :param movplate: integer plate id for moving plate [required]

    :param model: name for reconstruction model [defaults to default model from web service settings]

    :returns:  json containing reconstructed motion path features
    """
    seedpoints = request.GET.get("seedpoints", None)
    times = request.GET.get("timespec", "0,100,10")
    reconstruction_time = request.GET.get("time", 0)
    RelativePlate = request.GET.get("fixplate", 0)
    MovingPlate = request.GET.get("movplate", None)
    model = request.GET.get("model", settings.MODEL_DEFAULT)

    points = []
    if seedpoints:
        ps = seedpoints.split(",")
        if len(ps) % 2 == 0:
            for lat, lon in zip(ps[1::2], ps[0::2]):
                points.append((float(lat), float(lon)))

    seed_points_at_digitisation_time = pygplates.MultiPointOnSphere(points)

    if times:
        ts = times.split(",")
        if len(ts) == 3:
            times = np.arange(float(ts[0]), float(ts[1]) + 0.1, float(ts[2]))

    model_dict = get_reconstruction_model_dict(model)

    rotation_model = pygplates.RotationModel(
        [
            str("%s/%s/%s" % (settings.MODEL_STORE_DIR, model, rot_file))
            for rot_file in model_dict["RotationFile"]
        ]
    )

    # Create the motion path feature
    digitisation_time = 0
    # seed_points_at_digitisation_time = pygplates.MultiPointOnSphere([SeedPoint])
    motion_path_feature = pygplates.Feature.create_motion_path(
        seed_points_at_digitisation_time,
        times=times,
        valid_time=(2000, 0),
        relative_plate=int(RelativePlate),
        reconstruction_plate_id=int(MovingPlate),
    )

    # Create the shape of the motion path
    # reconstruction_time = 0
    reconstructed_motion_paths = []
    pygplates.reconstruct(
        motion_path_feature,
        rotation_model,
        reconstructed_motion_paths,
        float(reconstruction_time),
        reconstruct_type=pygplates.ReconstructType.motion_path,
    )

    data = {"type": "FeatureCollection"}
    data["features"] = []
    for reconstructed_motion_path in reconstructed_motion_paths:
        Dist = []
        for segment in reconstructed_motion_path.get_motion_path().get_segments():
            Dist.append(segment.get_arc_length() * pygplates.Earth.mean_radius_in_kms)
        feature = {"type": "Feature"}
        feature["geometry"] = {}
        feature["geometry"]["type"] = "LineString"
        #### NOTE CODE TO FLIP COORDINATES TO
        feature["geometry"]["coordinates"] = [
            (lon, lat)
            for lat, lon in reconstructed_motion_path.get_motion_path().to_lat_lon_list()
        ]
        feature["geometry"]["distance"] = Dist
        feature["properties"] = {}
        data["features"].append(feature)

    ret = json.dumps(round_floats(data))

    # add header for CORS
    # http://www.html5rocks.com/en/tutorials/cors/
    response = HttpResponse(ret, content_type="application/json")
    # TODO:
    response["Access-Control-Allow-Origin"] = "*"
    return response


def flowline(request):
    """
    http GET request to retrieve reconstructed flowline

    NOT YET IMPLEMENTED
    """

    # ret = json.dumps(round_floats(data))
    ret = "dummy"

    # add header for CORS
    # http://www.html5rocks.com/en/tutorials/cors/
    response = HttpResponse(ret, content_type="application/json")
    # TODO:
    response["Access-Control-Allow-Origin"] = "*"
    return response


@csrf_exempt
def html_model_list(request):

    # df = pd.read_csv(
    #   "%s/%s" % (settings.PALEO_STORE_DIR, "ngeo2429-s2.csv"),
    #    index_col="Deposit number",
    # )
    # html_table = df.to_html(index=False)
    html_table = "dummy"
    return render(request, "list_template.html", {"html_table": html_table})


# negative -- counter-clockwise
# positive -- clockwise
def check_polygon_orientation(lons, lats):
    lats = lats + lats[:1]
    lons = lons + lons[:1]
    length = len(lats)
    last_lon = lons[0]
    last_lat = lats[0]
    result = 0
    for i in range(1, length):
        result += (lons[i] - last_lon) * (lats[i] + last_lat)
        last_lon = lons[i]
        last_lat = lats[i]
    return result
