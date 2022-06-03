from datetime import datetime
from zoneinfo import ZoneInfo
import json
import sqlite3
import time

import requests as r

SLEEP = 5


def scrape_all(last_scrape_date):
    query = "keyword:look"

    # Get the total count of sequences.
    time.sleep(SLEEP)
    res = r.get("http://oeis.org/search", {"fmt": "json", "q": query})
    if res.status_code == 200:
        count = json.loads(res.text)["count"]
    else:
        count = 0
    print(f"Found {count} sequences matching query {query}.")

    for start in range(0, count, 10):
        results = scrape({"fmt": "json",
                          "q": query,
                          "start": start,
                          "sort": "modified"})

        latest_update_in_these_results = max(r["last_updated"] for r in results)
        if latest_update_in_these_results < last_scrape_date:
            break

        yield from scrape({"fmt": "json",
                           "q": query,
                           "start": start,
                           "sort": "modified"})

def scrape(params):
    time.sleep(SLEEP)
    res = r.get("http://oeis.org/search", params)

    res.raise_for_status()

    results = json.loads(res.text)["results"]
    return [{"id": seq["number"],
             "description": seq["name"],
             "last_updated": datetime.fromisoformat(seq["time"])}
            for seq in results]

def __main__():
    # TODO add tests
    con = sqlite3.connect("oeis.db")
    with con:
        cur = con.cursor()

        cur.execute('''CREATE TABLE IF NOT EXISTS sequences
                       (id integer primary key,
                        description text,
                        last_updated integer,
                        last_tweeted integer)''')
        cur.execute('''SELECT max(last_updated) FROM sequences''')
        last_scrape_date = cur.fetchone()[0] or datetime.fromtimestamp(0, tz=ZoneInfo("UTC"))
        print(last_scrape_date)

        for seq in scrape_all(last_scrape_date):
            print(seq)
            cur.execute('''INSERT INTO sequences VALUES (:id, :description, :last_updated, NULL)
                           ON CONFLICT(id) DO UPDATE SET last_updated=:last_updated''',
                        seq)
    con.close()

if __name__ == "__main__":
    __main__()
