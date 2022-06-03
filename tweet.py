from datetime import datetime
import io
import sqlite3

import requests as r
from PIL import Image
import tweepy

from secrets import API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET

auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
api = tweepy.API(auth)

def fetch_sequence(con, seq_id):
    with con:
        cur = con.cursor()
        if seq_id is None:
            cur.execute('''SELECT *
                           FROM sequences
                           WHERE (last_tweeted IS NULL)
                                 OR
                                 (last_tweeted < date('now', '-7 day'))
                           ORDER BY RANDOM()
                           LIMIT 1''')
        else:
            cur.execute('''SELECT *
                           FROM sequences
                           WHERE id=?''',
                        (seq_id,))
        seq = cur.fetchone()

        if seq is None:
            return

        return {'id': seq[0],
                'description': seq[1],
                'last_modified': datetime.fromisoformat(seq[2])}

def prepare_tweet(seq):
    text = f"oeis.org/A{seq['id']:06}\n\n{seq['description']}"

    res = r.get(f"https://oeis.org/A{seq['id']:06}/graph", {"png": 1})
    res.raise_for_status()

    all_plots = Image.open(io.BytesIO(res.content))
    width, height = all_plots.size

    plots = [all_plots.crop((0, upper, width, upper + 400))
             for upper in range(0, height, 400)]

    texts = []
    MAX_TWEET_LENGTH = 140
    while len(text) > 0:
        if len(text) <= MAX_TWEET_LENGTH:
            texts.append(text)
            text = ""
        else:
            last_space_index = text.rfind(" ", 0, MAX_TWEET_LENGTH)
            if last_space_index > -1:
                this_text = text[:last_space_index]
                text = text[last_space_index + 1:]
            else:
                this_text = text[:MAX_TWEET_LENGTH - 1]
                text = text[MAX_TWEET_LENGTH - 1:]
            texts.append(this_text + "…")

    return (texts, plots)


def tweet_sequence(api, seq):
    texts, plots = prepare_tweet(seq)

    media = []
    for idx, plot in enumerate(plots[1:]):
        fileobj = io.BytesIO()
        plot.save(fileobj, "PNG")
        fileobj.seek(0)
        media.append(api.media_upload(f"A{seq['id']:06}plot{idx + 1}.png",
                     file=fileobj))

    last_tweet = api.update_status(texts[0],
                                   media_ids=[m.media_id for m in media],
                                   tweet_mode="extended",
                                   )
    
    for text in texts[1:]:
        last_tweet = api.update_status(text,
                                       in_reply_to_status_id=last_tweet.id,
                                       tweet_mode="extended")
