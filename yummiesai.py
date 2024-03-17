from typing import List

import dotenv
from instagrapi import Client
import pickle
import argparse

from instagrapi.types import Media
import pandas as pd


class InstagramExtractor:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.client = Client()
        self.client.login(username, password)
        self.user_id = self.client.user_id_from_username(username)
        self.media = None

    def get_user_posts(self):
        media = self.client.user_medias(self.user_id)
        self.media = media
        print(f"found {len(media)} posts")
        return media

    def save_media_to_pickle(self, output_path: str):
        with open(output_path, "wb") as w:
            pickle.dump(self.media, w)
        print("saved media to file: ", output_path)


if __name__ == "__main__":
    dotenv.load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--type")
    args = parser.parse_args()

    if args.type == "extract":
        INSTAGRAM_USERNAME = dotenv.dotenv_values()["INSTAGRAM_USERNAME"]
        INSTAGRAM_PASSWORD = dotenv.dotenv_values()["INSTAGRAM_PASSWORD"]

        extractor = InstagramExtractor(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        posts = extractor.get_user_posts()
        extractor.save_media_to_pickle("output.pickle")
    elif args.type == "prompt":
        with open("output.pickle", "rb") as r:
            media: List[Media] = pickle.load(r)

        print("# of posts: ", len(media))

        PROMPT_HEAD = """You are given entries with the format <Entry:id>description</Entry:id>, output the data
        with their rating with the format entry_id:rating:food_category:summary. food_category should be a comma
        separated list of food categories, which are: fine dining, chinese, american, modern, indian, fast food, dining
        hall food, cheap, expensive, n/a (only if you can't tell).
        You can add more if none of these match. Rating should be within the text.
        Make sure to remove the /10 (if it exists). Otherwise, put n/a. If it's clear, you can assign rating based on
        sentiment. summary should be a brief description, or n/a. Stop output once you have processed all the entries.
        \n\n"""

        # prompt generation
        with open("prompt.txt", "w") as p:
            p.write(PROMPT_HEAD)

            for i, post in enumerate(media):
                p.write(f"<Entry:{i}>{post.caption_text}</Entry:{i}>\n")

        # TODO: call an LLM API, I did this manually w/ ChatGPT
    elif args.type == "label":
        with open("output.pickle", "rb") as r:
            media: List[Media] = pickle.load(r)

        df = pd.read_csv("response.txt", sep=":")
        df.columns = ["Index", "Rating", "Type", "Summary"]
        df.set_index("Index")


        def create_attribute_tuples(attributes):
            return {a: [(i, getattr(post, a)) for i, post in enumerate(media)] for a in attributes}


        attrs = create_attribute_tuples(["caption_text", "id", "title", "location", "usertags", "like_count"])

        for k, v in attrs.items():
            idx, values = zip(*v)
            series = pd.Series(values, index=idx)

            df[k] = series

        df.to_csv("output.csv")