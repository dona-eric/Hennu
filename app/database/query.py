from altair.datasets import url
from sqlalchemy import String, Any, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import create_engine




# create the engine of sqlite

engine = create_engine(url)