import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from config.settings import settings
from config.logger import logger

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    role = Column(String(50), default="admin")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False) # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, nullable=False)
    action_type = Column(String(100), nullable=False) # 'shell_command', 'gui_action', 'file_edit'
    details = Column(Text, nullable=False)
    risk_level = Column(String(20), nullable=False) # 'SAFE', 'MODERATE', 'CRITICAL'
    approved = Column(Boolean, default=True) # HITL status
    outcome = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# Engine & Session Maker
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all relational tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Relational database initialized successfully.")
        
        # Seed default admin if present
        session = SessionLocal()
        try:
            admin_ids = settings.admin_ids
            for admin_id in admin_ids:
                existing = session.query(User).filter(User.telegram_id == admin_id).first()
                if not existing:
                    user = User(telegram_id=admin_id, username="system_admin", role="admin")
                    session.add(user)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error seeding initial admin: {e}")
        finally:
            session.close()

    except Exception as e:
        logger.error(f"Failed to initialize relational database: {e}")

class RelationalMemory:
    """Helper manager to interact with the database without direct session boilerplates."""
    
    @staticmethod
    def add_chat_message(telegram_id: int, role: str, content: str):
        db = SessionLocal()
        try:
            message = ChatHistory(telegram_id=telegram_id, role=role, content=content)
            db.add(message)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to write chat history: {e}")
        finally:
            db.close()

    @staticmethod
    def get_chat_history(telegram_id: int, limit: int = 15) -> list:
        db = SessionLocal()
        try:
            results = db.query(ChatHistory)\
                .filter(ChatHistory.telegram_id == telegram_id)\
                .order_by(ChatHistory.timestamp.desc())\
                .limit(limit).all()
            # Return ordered chronologically
            return [{"role": r.role, "content": r.content} for r in reversed(results)]
        except Exception as e:
            logger.error(f"Failed to fetch chat history: {e}")
            return []
        finally:
            db.close()

    @staticmethod
    def log_audit(telegram_id: int, action_type: str, details: str, risk_level: str, approved: bool, outcome: str = None):
        db = SessionLocal()
        try:
            log = AuditLog(
                telegram_id=telegram_id,
                action_type=action_type,
                details=details,
                risk_level=risk_level,
                approved=approved,
                outcome=outcome
            )
            db.add(log)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to log audit: {e}")
        finally:
            db.close()
