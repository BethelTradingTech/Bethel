"""
Bethel Trading Technologies
Database Initialization
"""


from api.database import engine
from api.models import Base

# IMPORTANT
# Import authentication models
# so SQLAlchemy registers users table

from auth.models import User



print("Creating database tables...")


Base.metadata.create_all(
    bind=engine
)


print("Database ready!")