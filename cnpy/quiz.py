import json

from cnpy.db import db


def load_db():
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS quiz (
            v       TEXT NOT NULL PRIMARY KEY,
            srs     JSON,
            [data]  JSON
        );

        CREATE INDEX IF NOT EXISTS idx_quiz_srs_due ON quiz (json_extract(srs, '$.due'));
        CREATE INDEX IF NOT EXISTS idx_quiz_wordfreq ON quiz (json_extract([data], '$.wordfreq'));
        CREATE INDEX IF NOT EXISTS idx_quiz_sent_count ON quiz (json_array_length([data], '$.sent'));
        CREATE INDEX IF NOT EXISTS idx_quiz_count ON quiz (json_extract([data], '$.count'));

        CREATE TABLE IF NOT EXISTS revlog (
            v           TEXT NOT NULL,
            prev_srs    JSON,
            mark        INT NOT NULL,
            created     TEXT NOT NULL   -- TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_revlog_v ON revlog (v);
        CREATE INDEX IF NOT EXISTS idx_revlog_mark ON revlog (mark);
        CREATE INDEX IF NOT EXISTS idx_revlog_created_f ON revlog (unixepoch(created));

        DROP INDEX IF EXISTS idx_revlog_created;

        CREATE TABLE IF NOT EXISTS vlist (
            v           TEXT NOT NULL PRIMARY KEY,
            created     TEXT NOT NULL,  -- TIMESTAMP
            skip        INT,            -- boolean
            [data]      JSON
        );

        CREATE INDEX IF NOT EXISTS idx_vlist_created_f ON vlist (unixepoch(created));
        CREATE INDEX IF NOT EXISTS idx_vlist_skip ON vlist (skip);
        """
    )

    populate_db()


def load_db_entry(r):
    r = dict(r)

    for k in ("data", "srs"):
        if type(r.get(k, None)) is str:
            r[k] = json.loads(r[k])

    for k in list(r.keys()):
        if r[k] is None:
            del r[k]

    return r


def populate_db():
    pass
