import sys
import os
from datetime import date

# Ensure the app context is available
sys.path.insert(0, os.path.abspath('.'))
from app import create_app
from app.extensions import db
from app.models import Holiday

def seed_holidays():
    app = create_app()
    with app.app_context():
        # List of Indian holidays and Telangana Formation Day for 2026
        holidays_2026 = [
            # Fixed Date National Holidays
            {"name": "Republic Day", "date": date(2026, 1, 26), "holiday_type": "Public", "description": "National Holiday"},
            {"name": "Independence Day", "date": date(2026, 8, 15), "holiday_type": "Public", "description": "National Holiday"},
            {"name": "Gandhi Jayanti", "date": date(2026, 10, 2), "holiday_type": "Public", "description": "National Holiday"},
            
            # Telangana Specific
            {"name": "Telangana Formation Day", "date": date(2026, 6, 2), "holiday_type": "Public", "description": "State Holiday for Telangana"},
            
            # Major Festivals (2026 approximate/actual dates)
            {"name": "Makar Sankranti / Pongal", "date": date(2026, 1, 14), "holiday_type": "Restricted", "description": "Harvest Festival"},
            {"name": "Maha Shivaratri", "date": date(2026, 2, 13), "holiday_type": "Restricted", "description": "Hindu Festival"},
            {"name": "Holi", "date": date(2026, 3, 3), "holiday_type": "Public", "description": "Festival of Colors"},
            {"name": "Eid-ul-Fitr", "date": date(2026, 3, 20), "holiday_type": "Public", "description": "End of Ramadan"},
            {"name": "Ram Navami", "date": date(2026, 3, 26), "holiday_type": "Restricted", "description": "Birth of Lord Rama"},
            {"name": "Mahavir Jayanti", "date": date(2026, 3, 31), "holiday_type": "Restricted", "description": "Jain Festival"},
            {"name": "Good Friday", "date": date(2026, 4, 3), "holiday_type": "Public", "description": "Christian Holiday"},
            {"name": "Eid-ul-Adha (Bakrid)", "date": date(2026, 5, 27), "holiday_type": "Public", "description": "Festival of Sacrifice"},
            {"name": "Raksha Bandhan", "date": date(2026, 8, 28), "holiday_type": "Restricted", "description": "Bond of Protection"},
            {"name": "Janmashtami", "date": date(2026, 9, 4), "holiday_type": "Restricted", "description": "Birth of Lord Krishna"},
            {"name": "Ganesh Chaturthi", "date": date(2026, 9, 14), "holiday_type": "Public", "description": "Ganesha Festival"},
            {"name": "Dussehra (Vijayadashami)", "date": date(2026, 10, 19), "holiday_type": "Public", "description": "Victory of Good over Evil"},
            {"name": "Diwali (Deepavali)", "date": date(2026, 11, 8), "holiday_type": "Public", "description": "Festival of Lights"},
            {"name": "Guru Nanak Jayanti", "date": date(2026, 11, 24), "holiday_type": "Public", "description": "Sikh Festival"},
            {"name": "Christmas", "date": date(2026, 12, 25), "holiday_type": "Public", "description": "Christian Festival"}
        ]

        count = 0
        for h in holidays_2026:
            # Check if this holiday already exists to avoid duplicates
            existing = Holiday.query.filter_by(date=h["date"], name=h["name"]).first()
            if not existing:
                new_holiday = Holiday(
                    name=h["name"],
                    date=h["date"],
                    holiday_type=h["holiday_type"],
                    description=h["description"]
                )
                db.session.add(new_holiday)
                count += 1
        
        db.session.commit()
        print(f"Successfully added {count} holidays to the database!")

if __name__ == '__main__':
    seed_holidays()
