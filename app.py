import sys


if sys.version_info < (3, 9):
    raise SystemExit(
        "This service requires Python 3.9+ and cannot run with Python 2. "
        "Use: py -3 app.py"
    )

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])