"""
Time-varying load for hotelReservation, following socialNetwork/locust/locust_*.py.

One Locust process per request stream (as the Social Network runs), chosen with
HOTEL_REQUEST = search | recommend | reserve. RPS per second is read from the single-column
CSV in HOTEL_CSV; each second Locust runs that many users, each issuing about one request
per second (exponential think time), so the request rate follows the CSV.
Requests reproduce hotelReservation/wrk2/scripts/hotel-reservation/mixed-workload_type_1.lua.
The 'reserve' stream mixes user login (50%) and reservation (50%).
"""
import csv
import math
import os
import random

from locust import HttpUser, LoadTestShape, task

REQUEST = os.getenv("HOTEL_REQUEST", "search")


def _date(day):
    return f"2015-04-{day:02d}"


def _coords():
    lat = 38.0235 + (random.randint(0, 481) - 240.5) / 1000.0
    lon = -122.095 + (random.randint(0, 325) - 157.0) / 1000.0
    return lat, lon


def _user():
    uid = random.randint(0, 500)
    return f"Cornell_{uid}", str(uid) * 10


class HotelUser(HttpUser):
    host = os.getenv("LOCUST_HOST", "http://localhost:5000")

    def wait_time(self):
        return random.expovariate(1.0)

    @task
    def request(self):
        if REQUEST == "search":
            d_in = random.randint(9, 23)
            d_out = random.randint(d_in + 1, 24)
            lat, lon = _coords()
            self.client.get(f"/hotels?inDate={_date(d_in)}&outDate={_date(d_out)}&lat={lat}&lon={lon}",
                            name="search_hotels")
        elif REQUEST == "recommend":
            req = random.choice(["dis", "rate", "price"])
            lat, lon = _coords()
            self.client.get(f"/recommendations?require={req}&lat={lat}&lon={lon}", name="recommend")
        elif REQUEST == "reserve":
            user, pw = _user()
            if random.random() < 0.5:
                self.client.post(f"/user?username={user}&password={pw}", name="user_login")
            else:
                d_in = random.randint(9, 23)
                d_out = d_in + random.randint(1, 5)
                lat, lon = _coords()
                self.client.post(
                    f"/reservation?inDate={_date(d_in)}&outDate={_date(d_out)}&lat={lat}&lon={lon}"
                    f"&hotelId={random.randint(1, 80)}&customerName={user}&username={user}"
                    f"&password={pw}&number=1", name="reserve")
        else:
            raise ValueError(f"unknown HOTEL_REQUEST {REQUEST}")


class CsvShape(LoadTestShape):
    """Users per second from HOTEL_CSV; stops when the CSV ends (as HomeTimelineCsvShape)."""
    csv_path = os.getenv("HOTEL_CSV", "workload.csv")

    def __init__(self):
        super().__init__()
        self.rps = []
        with open(self.csv_path) as f:
            for row in csv.reader(f):
                if row and row[0].strip().lstrip("-").isdigit():
                    self.rps.append(max(int(row[0]), 0))

    def tick(self):
        i = int(math.floor(self.get_run_time()))
        if i >= len(self.rps):
            return None
        return self.rps[i], max(self.rps[i], 1)
