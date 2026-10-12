"""WSGI entry point, also usable with `python main.py`."""

import os

from educonnect import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5001")))
