import csv
import sqlite3
from datetime import datetime
import dotenv

from typing import Callable, Any

env = dotenv.dotenv_values()

table_name = "quiz"
select = """
json_extract("data", '$.notes')         "notes",
replace(replace(json_extract("data", '$.pinyin'),'[','{'),']','}')      "reading",
replace(replace(json_extract("data", '$.mustPinyin'),'[','{'),']','}')  "must",
replace(replace(json_extract("data", '$.warnPinyin'),'[','{'),']','}')  "warn",
*
"""
where = """
WHERE coalesce(
    srs,
    "notes",
    "reading",
    "must",
    "warn"
) IS NOT NULL
"""

row_mapping: dict[str, Callable[[dict[str, Any]], Any]] = {
    "created_at": lambda r: r["created"] + "+07" if r.get("created") else None,
    "updated_at": lambda r: r["modified"] + "+07" if r.get("modified") else None,
    "user_id": lambda _: env["SUPABASE_USER_ID"],
}

removed_rows = [
    "data",
    "created",
    "modified",
]

db = sqlite3.connect("user/main.db")
db.row_factory = sqlite3.Row

csv_filepath = f"export/{table_name}.csv"

with open(csv_filepath, mode="w", newline="", encoding="utf8") as f:
    writer = csv.writer(f)
    headers = None

    for row in db.execute(f"SELECT {select} FROM {table_name} {where}"):
        d = dict(row)
        if not headers:
            headers = list(set((*d.keys(), *row_mapping.keys())))
            headers = [k for k in headers if not k in removed_rows]
            writer.writerow(headers)

        ls = []
        for k in headers:
            if k in row_mapping:
                ls.append(row_mapping[k](d))
            else:
                ls.append(d[k])

        writer.writerow(ls)
