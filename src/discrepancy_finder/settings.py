from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    url: str
    user: str
    password: str
    name: str
    scheme: str = 'mongodb+srv'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='DF_', case_sensitive=False, env_nested_delimiter='__',
                                      env_file='.env')

    database: DatabaseSettings

    @property
    def mongo_url(self):
        return f"{self.database.scheme}://{self.database.user}:{self.database.password}@{self.database.url}"
