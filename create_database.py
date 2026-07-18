from api.database import engine
from api.models import Base


print("Creating database tables...")


Base.metadata.create_all(
    bind=engine
)


print("Database ready!")