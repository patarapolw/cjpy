from fsrs import FSRS, Card, Rating
from regex import Regex

import json
import random
import datetime
from pprint import pprint

from cjpy.db import db
from cjpy.dir import exe_root


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

f_srs = FSRS()


class Api:
    def log(self, obj):
        pprint(obj, indent=1)

    def stats(self):
        def de_json(r):
            r = dict(r)

            for k in ("data", "srs"):
                if type(r[k]) is str:
                    r[k] = json.loads(r[k])

            return r

        studied = [
            de_json(r)
            for r in db.execute(
                """
            SELECT * FROM quiz
            WHERE json_extract(srs, '$.due') IS NOT NULL
            ORDER BY json_extract([data], '$.wordfreq') DESC
            """
            )
        ]

        studied.sort(key=lambda v: v.get("data", {}).get("wordfreq", 0), reverse=True)

        stats = {
            "studied": len(studied),
            "p95": studied[int(len(studied) * 0.95)]["data"]["wordfreq"],
        }

        for r in studied:
            f = r["data"]["wordfreq"]

            # stats.setdefault("upper", f)
            stats["rarest"] = f

            if f >= 6:
                pass
            elif f >= 5:
                k = "5.x"
                stats[k] = stats.setdefault(k, 0) + 1
            elif f >= 4:
                k = "4.x"
                stats[k] = stats.setdefault(k, 0) + 1
            elif f >= 3:
                k = "3.x"
                stats[k] = stats.setdefault(k, 0) + 1
            elif f >= 2:
                k = "2.x"
                stats[k] = stats.setdefault(k, 0) + 1
            elif f >= 1:
                k = "1.x"
                stats[k] = stats.setdefault(k, 0) + 1
            else:
                k = "0.x"
                stats[k] = stats.setdefault(k, 0) + 1

        return stats

    def due_vocab_list(self, count=20):
        rs = []

        now = datetime.datetime.now(datetime.UTC).isoformat().split(".", 1)[0]
        # self.log(now)

        skip_voc = self._get_custom_list(exe_root / "user/skip")

        all_items = list(
            db.execute(
                """
                SELECT * FROM quiz
                WHERE json_extract(srs, '$.due') < ?
                AND {}
                """.format(
                    "v NOT IN ('{}')".format("','".join(skip_voc))
                    if skip_voc
                    else "TRUE"
                ),
                (now,),
            ).fetchall()
        )

        more_voc = self._get_custom_list(exe_root / "user/vocab")

        for it in skip_voc:
            more_voc.remove(it)

        if more_voc:
            all_items.extend(
                db.execute(
                    """
                    SELECT * FROM quiz
                    WHERE v IN (
                        SELECT DISTINCT simp FROM cedict WHERE simp IN ('{}')
                    ) AND srs IS NULL
                    """.format(
                        "','".join(more_voc)
                    )
                )
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

        skip_voc = self._get_custom_list(exe_root / "user/skip")

        all_items = list(
            db.execute(
                """
                SELECT * FROM quiz
                WHERE srs IS NULL
                AND {}
                ORDER BY json_extract([data], '$.wordfreq') DESC
                LIMIT 1000
                """.format(
                    "v NOT IN ('{}')".format("','".join(skip_voc))
                    if skip_voc
                    else "TRUE"
                ),
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

        sentences = [
            dict(r)
            for r in db.execute(
                """
            SELECT *
            FROM sentence
            WHERE id IN (
                SELECT json_each.value
                FROM quiz, json_each(json_extract([data], '$.sent'))
                WHERE v = ?
            )
            AND eng IS NOT NULL
            AND LENGTH(cmn) < 30
            ORDER BY RANDOM()
            LIMIT 5
            """,
                (v,),
            )
        ]

        if len(sentences) < 3:
            prev_ids = set(r["id"] for r in sentences)

            for r in db.execute(
                """
            SELECT *
            FROM sentence
            WHERE id IN (
                SELECT json_each.value
                FROM quiz, json_each(json_extract([data], '$.sent'))
                WHERE v = ?
            )
            ORDER BY RANDOM()
            LIMIT 5
            """,
                (v,),
            ):
                r = dict(r)
                if r["id"] not in prev_ids:
                    sentences.append(r)

        return {"cedict": rs, "sentences": sentences[:5]}

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
        # self.log(card.to_dict())

        if not db.execute(
            "UPDATE quiz SET srs = ? WHERE v = ?",
            (card_json, v),
        ).rowcount:
            db.execute(
                "INSERT INTO quiz (v, srs) VALUES (?, ?)",
                (v, card_json),
            )

        db.commit()

    def _get_custom_list(self, path: "Path") -> set[str]:
        items = []
        re_han = Regex(r"^\p{Han}+$")

        for f in path.glob("**/*.txt"):
            items.extend(
                v
                for v in f.read_text(encoding="utf8").splitlines()
                if re_han.fullmatch(v)
            )

        return set(items)
