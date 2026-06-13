import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Try importing SQLAlchemy
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, declarative_base
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logger.warning("SQLAlchemy is not installed. Database persistence is disabled.")

engine = None
SessionLocal = None
Base = None

if SQLALCHEMY_AVAILABLE:
    try:
        db_url = settings.database_url
        # SQLite compatibility helper (e.g. for testing)
        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            
        engine = create_engine(db_url, connect_args=connect_args)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base = declarative_base()
        logger.info(f"Database engine configured with URL: {db_url}")
    except Exception as e:
        logger.error(f"Error initializing database engine: {str(e)}")
        SQLALCHEMY_AVAILABLE = False

def get_db():
    if not SQLALCHEMY_AVAILABLE or SessionLocal is None:
        yield None
        return
        
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()
