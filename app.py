import webview

from cjpy import load_db
from cjpy.api import Api


if __name__ == "__main__":
    load_db()

    api = Api()

    win = webview.create_window(
        "Pinyin Quiz",
        "web/quiz.html",
        js_api=api,
    )
    webview.start(lambda: win.evaluate_js("newVocab()"))

    api.log(api.stats())
