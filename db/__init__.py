from db.engine import get_engine
from db.schema import metadata

def init_db():
    engine = get_engine()
    metadata.create_all(engine)
