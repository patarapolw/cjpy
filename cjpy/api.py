from fsrs import *

import json
import random
import datetime
from pprint import pprint

from cjpy.db import db

f_srs = FSRS()


class Api:
    def log(self, obj):
        pprint(obj, indent=1)

    def due_vocab_list(self, count=20):
        rs = []

        now = datetime.datetime.now(datetime.UTC).isoformat().split(".", 1)[0]
        self.log(now)

        all_items = list(
            db.execute(
                """
            SELECT * FROM quiz
            WHERE json_extract(srs, '$.due') < ?
            ORDER BY json_extract([data], '$.wordfreq') DESC
            """,
                (now,),
            ).fetchall()
        )

        for r in (
            random.sample(
                all_items,
                k=count,
            )
            if len(all_items) > count
            else random.shuffle(all_items) or all_items
        ):
            r = dict(r)

            for k in ("data", "srs"):
                if type(r[k]) is str:
                    r[k] = json.loads(r[k])

            for k in list(r.keys()):
                if r[k] is None:
                    del r[k]

            rs.append(r)

        return {"result": rs, "count": len(all_items)}

    def new_vocab_list(self, count=20):
        rs = []

        all_items = list(
            db.execute(
                """
            SELECT * FROM quiz
            WHERE srs IS NULL
            ORDER BY json_extract([data], '$.wordfreq') DESC
            LIMIT 1000
            """,
            ).fetchall()
        )

        for r in (
            random.sample(
                all_items,
                k=count,
            )
            if len(all_items) > count
            else random.shuffle(all_items) or all_items
        ):
            r = dict(r)

            for k in ("data", "srs"):
                if type(r[k]) is str:
                    r[k] = json.loads(r[k])

            for k in list(r.keys()):
                if r[k] is None:
                    del r[k]

            rs.append(r)

        return {"result": rs}

    def vocab_details(self, v: str):
        rs = []

        for r in db.execute("SELECT * FROM cedict WHERE simp = ?", (v,)):
            r = dict(r)

            for k in ("data", "english"):
                if type(r[k]) is str:
                    r[k] = json.loads(r[k])

            for k in list(r.keys()):
                if r[k] is None:
                    del r[k]

            rs.append(r)

        return rs

    def mark(self, v: str, t: str):
        card = Card()

        for r in db.execute("SELECT srs FROM quiz WHERE v = ? LIMIT 1", (v,)):
            if type(r["srs"]) is str:
                card = Card.from_dict(json.loads(r["srs"]))
                break

        card, review_log = f_srs.review_card(
            card,
            {"right": Rating.Good, "repeat": Rating.Hard, "wrong": Rating.Again}[t],
        )

        card_json = json.dumps(card.to_dict())
        self.log(card.to_dict())

        if not db.execute(
            "UPDATE quiz SET srs = ? WHERE v = ?",
            (card_json, v),
        ).rowcount:
            db.execute(
                "INSERT INTO quiz (v, srs) VALUES (?, ?)",
                (v, card_json),
            )

        db.commit()
