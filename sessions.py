
from app import app, db, Session

from datetime import datetime, timedelta
def send_notifications():
    with app.app_context():
        # Check for sessions in next 24 hours
        upcoming = Session.query.filter(
            Session.scheduled_time > datetime.utcnow(),
            Session.scheduled_time <= datetime.utcnow() + timedelta(hours=24),
            Session.notification_sent == False
        ).all()

        for session in upcoming:
            # In real implementation, add email/SMS code here
            print(f"Reminder: Session {session.id} at {session.scheduled_time}")
            session.notification_sent = True
            db.session.commit()