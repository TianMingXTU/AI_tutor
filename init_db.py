# personal_ai_tutor/init_db.py
from src.tutor_app.db.session import engine
from src.tutor_app.db.models import Base

def init_database():
    print("Creating all database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")

if __name__ == "__main__":
    init_database()