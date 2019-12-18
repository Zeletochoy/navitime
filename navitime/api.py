import json
import re
from math import sqrt
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.navitime.co.jp"
POI_RE = re.compile(r"setPOI\(([^)]+)\);")


@dataclass
class AddressResult:
    index: int
    longitude: float
    latitude: float
    code: str
    name: str
    address: Optional[str]
    telephone: Optional[str]
    catcode: Optional[str]
    mapid: Optional[str]
    spotid: Optional[str]
    groupid: Optional[str]
    advid: Optional[str]

    @classmethod
    def from_re_match(cls, match: re.Match) -> "AddressResult":
        args = list(eval(match[1].replace("null", "None")))
        args += [None] * (12 - len(args))
        return cls(*args)

    def get_route_params(self, road_type="default"):
        params = {
            "name": self.name,
            "lat": self.latitude,
            "lon": self.longitude,
            "road-type": road_type,
        }
        if self.code:
            params["node"] = self.code
        elif self.mapid and self.spotid:
            params["spot"] = f"{self.mapid}-{self.spotid}"
        else:
            raise NotImplementedError("Don't know how to build route params from provided ids")
        return params

    def get_poi_params(self):
        params = {
            "_": int(datetime.now().timestamp()),
        }
        if self.code:
            params["id"] = self.code
        elif self.mapid and self.spotid:
            params["code"] = f"{self.mapid}-{self.spotid}"
        else:
            raise NotImplementedError("Don't know how to build poi params from provided ids")
        return params


def address_search(query: str) -> List[AddressResult]:
    res = requests.get(BASE_URL, params={"keyword": query, "set": 0, "ctl": 100401})
    soup = BeautifulSoup(res.content.decode("utf-8"), "html.parser")
    onclicks = [a["onclick"] for a in soup("a")]
    if not onclicks:
        # Weird behaviour, sometimes it just returns a function call...
        onclicks = [str(soup)]
    matches = [POI_RE.match(o) for o in onclicks]
    return [AddressResult.from_re_match(m) for m in matches if m is not None]


def refine_address_coordinates(address: AddressResult) -> None:
    params = address.get_poi_params()
    res = requests.get(f"{BASE_URL}/maps/async/poi", params=params)
    pos = res.json().get("coord")
    if pos is not None:
        address.latitude = pos.get("lat", address.latitude)
        address.longitude = pos.get("lon", address.longitude)


def _get_route_query_params(start: AddressResult, goal: AddressResult, speed: int = 15) -> dict:
    return {
        "bicycle": "only.multi.turn",
        "start-time": datetime.now().isoformat().rsplit(".", 1)[0],
        "start": json.dumps(start.get_route_params(), ensure_ascii=False),
        "goal": json.dumps(goal.get_route_params(), ensure_ascii=False),
        "bicycle-speed": speed,
    }


def get_route_url(start: AddressResult, goal: AddressResult, speed=15) -> str:
    params = _get_route_query_params(start, goal, speed)
    return f"{BASE_URL}/maps/routeResult?{urlencode(params)}"


def get_gmaps_nav_url(start: AddressResult, goal: AddressResult) -> str:
    params = _get_route_query_params(start, goal)
    res = requests.get(f"{BASE_URL}/maps/route/shape", params=params)
    shape_json = res.json()
    stops = []
    for stop in shape_json["features"]:
        for coords in stop["geometry"]["coordinates"]:
            coords = coords[::-1]
            if not stops or coords != stops[-1]:
                stops.append(coords)
    stops = _filter_waypoints(stops)
    stops = [f"{stop[0]},{stop[1]}" for stop in stops]
    params = {
        "travelmode": "walking",
        "origin": stops[0],
        "destination": stops[-1],
    }
    if len(stops) > 2:
        params["waypoints"] = "|".join(stops[max(1, len(stops)-10):-1])
    return f"https://www.google.com/maps/dir/?api=1&{urlencode(params)}"


def _filter_waypoints(waypoints):
    if len(waypoints) <= 11:
        return waypoints
    plat, plon = waypoints[0]
    dists = []
    total_dist = 0
    for lat, lon in waypoints[1:]:
        dist = sqrt((lat - plat) ** 2 + (lon - plon) ** 2)
        total_dist += dist
        dists.append(dist)
        plat, plon = lat, lon
    target = total_dist / 10
    cur = 0
    used = 0
    filtered = [waypoints[0]]
    for i, d in enumerate(dists):
        if cur + d < target:
            cur += d
        elif len(filtered) == 10:
            filtered.append(waypoints[-1])
            break
        else:
            used += cur
            target = (total_dist - used) / (11 - len(filtered))
            filtered.append(waypoints[i])
            cur = d
    return filtered
