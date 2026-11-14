import os
import random
import string
from locust import HttpUser, task, between

class ComposePostUser(HttpUser):
    # Target host (can be overridden via --host on the CLI)
    host = os.getenv("LOCUST_HOST", "http://localhost:8080")
    # Pause between tasks: here a fixed wait, but you can randomize if you like
    wait_time = between(0.5, 1.5)

    # Load max_user_index from environment (default to 962 if not set)
    max_user_index = int(os.getenv("max_user_index", "962"))

    # Pre‐build “charset” and “decset” arrays just like in Lua
    charset = list(string.ascii_lowercase + string.ascii_uppercase + string.digits)
    decset = list(string.digits)

    def random_string(self, length):
        """
        Generate a random string of `length` characters, 
        choosing from [a-zA-Z0-9].
        """
        return "".join(random.choices(self.charset, k=length))

    def decimal_string(self, length):
        """
        Generate a random string of `length` decimal digits [0-9].
        """
        return "".join(random.choices(self.decset, k=length))

    @task
    def compose_post(self):
        # 1) Pick a random user index
        user_index = random.randint(0, self.max_user_index - 1)
        username = f"username_{user_index}"
        user_id = str(user_index)

        # 2) Build a 256‐character random “text” payload
        text = self.random_string(256)

        # 3) Random numbers of mentions, URLs, and media
        num_user_mentions = random.randint(0, 5)
        num_urls = random.randint(0, 5)
        num_media = random.randint(0, 4)

        # 4) Append “@username_X” mentions
        for _ in range(num_user_mentions):
            # Pick a different user‐mention than the author
            while True:
                mention_id = random.randint(0, self.max_user_index - 1)
                if mention_id != user_index:
                    break
            text += f" @username_{mention_id}"

        # 5) Append “ http://<64‐char random>” URLs
        for _ in range(num_urls):
            text += " http://" + self.random_string(64)

        # 6) Build media_ids and media_types arrays (as JSON‐style strings)
        if num_media > 0:
            media_ids_list = []
            media_types_list = []
            for _ in range(num_media):
                # Each media_id is an 18‐digit decimal string
                media_id = self.decimal_string(18)
                media_ids_list.append(f"\"{media_id}\"")
                media_types_list.append("\"png\"")

            media_ids_str = "[" + ",".join(media_ids_list) + "]"
            media_types_str = "[" + ",".join(media_types_list) + "]"
        else:
            # No media
            media_ids_str = "[]"
            media_types_str = "[]"

        # 7) Prepare form‐data payload
        payload = {
            "username": username,
            "user_id": user_id,
            "text": text,
            "media_ids": media_ids_str,
            "media_types": media_types_str,
            "post_type": "0",
        }

        # 8) Send a POST to /wrk2-api/post/compose with form‐encoded data
        # Locust will set “Content-Type: application/x-www-form-urlencoded” automatically
        with self.client.post(
            "/wrk2-api/post/compose",
            data=payload,
            catch_response=True
        ) as response:
            # (Optional) You can check for expected status or content:
            if response.status_code != 200:
                response.failure(f"Got unexpected HTTP {response.status_code}")

