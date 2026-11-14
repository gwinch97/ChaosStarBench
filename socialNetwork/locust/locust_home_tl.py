import os
import csv
import math
import random
from locust import HttpUser, TaskSet, task, LoadTestShape

class HomeTimelineBehavior(TaskSet):
    @task
    def read_home_timeline(self):
        """
        Issue a GET to /wrk2-api/home-timeline/read with:
          - user_id  = random [0..max_user_index-1]
          - start    = random [0..100]
          - stop     = start + 10
        """
        uid = random.randint(0, self.user.max_user_index - 1)
        start = random.randint(0, 100)
        stop = start + 10

        query = f"user_id={uid}&start={start}&stop={stop}"
        with self.client.get(
            f"/wrk2-api/home-timeline/read?{query}",
            name="read_home_timeline",
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Unexpected HTTP {response.status_code}")

class HomeTimelineUser(HttpUser):
    """
    Each virtual user will run HomeTimelineBehavior as fast as possible.
    """
    host = os.getenv("LOCUST_HOST", "http://localhost:8080")
    
    def wait_time(self):
        return random.expovariate(1.0)

    tasks = [HomeTimelineBehavior]
    # allow overriding from env, default to 962
    max_user_index = int(os.getenv("max_user_index", "962"))

class HomeTimelineCsvShape(LoadTestShape):
    """
    Reads a single-column CSV of integers (RPS per second) from HOME_TL_CSV.
    Each second, spawns exactly that many HomeTimelineUser instances.
    When the CSV is exhausted, the test stops.
    """
    csv_path = os.getenv("HOME_TL_CSV", "home_tl_rps.csv")

    def __init__(self):
        super().__init__()
        self.rps_list = []
        try:
            with open(self.csv_path, "r") as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row:
                        continue
                    try:
                        val = int(row[0].strip())
                        self.rps_list.append(val)
                    except ValueError:
                        # skip blank or invalid lines
                        continue
        except FileNotFoundError:
            print(f"ERROR: Could not find HOME_TL_CSV at '{self.csv_path}'")
            self.rps_list = []

    def tick(self):
        run_time = self.get_run_time()          # seconds since test start (float)
        index = int(math.floor(run_time))       # floor to nearest full second

        # If we've run out of CSV entries, stop the test
        if index >= len(self.rps_list):
            return None

        target_rps = self.rps_list[index]
        if target_rps < 0:
            target_rps = 0

        # Spawn exactly target_rps users, ramping up in ~1 second
        user_count = target_rps
        spawn_rate = max(target_rps, 1)
        return (user_count, spawn_rate)

