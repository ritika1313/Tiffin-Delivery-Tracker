from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = "sqlite:///./dabawala.db"


engine = create_engine(DATABASE_URL, echo=True)

def create_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    """Provide a new database session.
    """
    with Session(engine) as session:
        yield session