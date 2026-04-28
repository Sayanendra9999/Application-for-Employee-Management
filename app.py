"""Entry point — run the Enterprise Portal."""

from dotenv import load_dotenv
load_dotenv()  # Load .env file before anything else

from app import create_app
from app.extensions import db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
