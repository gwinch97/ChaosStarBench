import os
import csv
import math
import random
import string
from locust import HttpUser, TaskSet, task, between, constant_throughput, LoadTestShape
import gevent

class UserBehavior(TaskSet):
    """
    A TaskSet for composing and sending /wrk2-api/post/compose requests.
    Task logic remains unchanged: it picks random user_index, random text,
    mentions, URLs, media_ids, etc., and posts to the endpoint.
    """

    @task
    def compose_post(self):
        # 1) Pick a random user_index via the helper on the parent HttpUser
        user_index = self.user.user_index_generator()
        username = f"username_{user_index}"
        user_id = str(user_index)

        # 2) Build a 256-char random "text" string
        text = self.user.random_string(256)

        # 3) Append random mentions (0..5)
        num_user_mentions = random.randint(0, 5)
        for _ in range(num_user_mentions):
            while True:
                mention_id = random.randint(0, self.user.max_user_index - 1)
                if mention_id != user_index:
                    break
            text += f" @username_{mention_id}"

        # 4) Append random URLs (0..5)
        num_urls = random.randint(0, 5)
        for _ in range(num_urls):
            text += " http://" + self.user.random_string(64)

        # 5) Append random media (0..4)
        num_media = random.randint(0, 4)
        if num_media > 0:
            media_ids_list = []
            media_types_list = []
            for _ in range(num_media):
                mid = self.user.decimal_string(18)  # 18-digit random decimal
                media_ids_list.append(f"\"{mid}\"")
                media_types_list.append("\"png\"")
            media_ids_str = "[" + ",".join(media_ids_list) + "]"
            media_types_str = "[" + ",".join(media_types_list) + "]"
        else:
            media_ids_str = "[]"
            media_types_str = "[]"

        # 6) Package payload as form-encoded data
        payload = {
            "username": username,
            "user_id": user_id,
            "text": text,
            "media_ids": media_ids_str,
            "media_types": media_types_str,
            "post_type": "0",
        }

        # 7) Send POST to /wrk2-api/post/compose
        with self.client.post(
            "/wrk2-api/post/compose",
            data=payload,
            catch_response=True,
            name="compose_post"
        ) as response:
            if response.status_code != 200:
                response.failure(f"Unexpected HTTP {response.status_code}")
        

class WebsiteUser(HttpUser):
    """
    Each Locust user runs the UserBehavior TaskSet. All helper methods
    (random_string, decimal_string, user_index_generator) and attributes
    (max_user_index, charset, decset) are defined here.
    """
    # Base target host (override with --host, if desired)
    host = os.getenv("LOCUST_HOST", "http://localhost:8080")
    # Users will loop through tasks as fast as possible (tiny wait_time)
    #wait_time = between(0.5, 1.0)
    def wait_time(self):
        return random.expovariate(1.0)
    
    # Load max_user_index from environment, default to 962
    max_user_index = int(os.getenv("max_user_index", "962"))

    # Pre-build charset (alphanumeric) and decset (digits only)
    charset = list(string.ascii_lowercase + string.ascii_uppercase + string.digits)
    decset = list(string.digits)

    tasks = [UserBehavior]

    def random_string(self, length: int) -> str:
        """Return a random alphanumeric string of length `length`."""
        return "".join(random.choices(self.charset, k=length))

    def decimal_string(self, length: int) -> str:
        """Return a random decimal-only string of length `length`."""
        return "".join(random.choices(self.decset, k=length))

    @staticmethod
    def user_index_generator() -> int:
        """
        Return a random user index in [0, max_user_index-1].
        Accessed as WebsiteUser.user_index_generator().
        """
        max_idx = WebsiteUser.max_user_index
        return random.randint(0, max_idx - 1)

class CsvLoadShape(LoadTestShape):
    """
    A LoadTestShape that reads 'rps_timeseries.csv' and sets user_count
    = target_rps each second. Returns (user_count, spawn_rate) per tick.
    When CSV is exhausted, returns None to stop the test.
    """
    csv_path = os.getenv("COMPOSE_CSV", "rps_timeseries.csv")

    def __init__(self):
        super().__init__()
        # Read all CSV lines into a list of ints
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
                        # Skip invalid lines
                        continue
        except FileNotFoundError:
            print(f"ERROR: Could not find RPS CSV at '{self.csv_path}'")
            self.rps_list = []

    def tick(self):
        """
        Called by Locust approximately once per second.
        Returns (user_count, spawn_rate) or None to stop.
        """
        run_time = self.get_run_time()          # Seconds since test start (float)
        index = int(math.floor(run_time))       # Floor to nearest whole second

        # If we've run out of CSV entries, stop the test
        if index >= len(self.rps_list):
            return None

        # Desired RPS from CSV for this second
        target_rps = self.rps_list[index]
        if target_rps < 0:
            target_rps = 0

        # Map RPS → user_count (1 user approximates 1 req/sec)
        user_count = target_rps
        # Choose spawn_rate so we can ramp to user_count within ~1 second
        spawn_rate = max(user_count, 1)

        return (user_count, 5)

