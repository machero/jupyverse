import sys
from pathlib import Path
from typing import Optional

import databases  # type: ignore
import sqlalchemy  # type: ignore
from fastapi_users import models  # type: ignore
from fastapi_users.db import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase  # type: ignore
from fastapi_users.db import SQLAlchemyBaseOAuthAccountTable  # type: ignore
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base  # type: ignore
from sqlalchemy import Boolean, String, Column
from fps.config import Config  # type: ignore

from .config import AuthConfig

auth_config = Config(AuthConfig)


class User(models.BaseUser, models.BaseOAuthAccountMixin):
    initialized: bool = False
    anonymous: bool = True
    name: Optional[str] = None
    username: Optional[str] = None
    color: Optional[str] = None
    avatar: Optional[str] = None
    logged_in: bool = False


class UserCreate(models.BaseUserCreate):
    name: Optional[str] = None
    username: Optional[str] = None
    color: Optional[str] = None


class UserUpdate(User, models.BaseUserUpdate):
    pass


class UserDB(User, models.BaseUserDB):
    pass


# FIXME: where do we want the DB?
userdb_dir = Path(sys.prefix) / "share" / "jupyter" / "jupyverse"
userdb_dir.mkdir(parents=True, exist_ok=True)
userdb_path = userdb_dir / "user.db"
if auth_config.clear_db and userdb_path.is_file():
    userdb_path.unlink()

DATABASE_URL = f"sqlite:///{userdb_path}"

database = databases.Database(DATABASE_URL)

Base: DeclarativeMeta = declarative_base()


class UserTable(Base, SQLAlchemyBaseUserTable):
    initialized = Column(Boolean, default=False, nullable=False)
    anonymous = Column(Boolean, default=False, nullable=False)
    name = Column(String(length=32), nullable=True)
    username = Column(String(length=32), nullable=True)
    color = Column(String(length=32), nullable=True)
    avatar = Column(String(length=32), nullable=True)
    logged_in = Column(Boolean, default=False, nullable=False)


class OAuthAccount(SQLAlchemyBaseOAuthAccountTable, Base):
    pass


engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

Base.metadata.create_all(engine)

users = UserTable.__table__
oauth_accounts = OAuthAccount.__table__
user_db = SQLAlchemyUserDatabase(UserDB, database, users, oauth_accounts)