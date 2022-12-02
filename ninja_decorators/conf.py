from django.conf import settings as django_settings
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Alter these by modifying the values in Django's settings module (usually `settings.py`)."""

    FILTER_CLASS: str = Field(
        "ninja_decorators.filtering.ORMFilter", alias="NINJA_DECORATORS_FILTER_CLASS"
    )
    SORTER_CLASS: str = Field(
        "ninja_decorators.sorting.ORMSorting", alias="NINJA_DECORATORS_SORTING_CLASS"
    )
    PERMISSIONS_CLASS: str = Field(
        "ninja_decorators.permissions.DjangoAuthPermissions",
        alias="NINJA_DECORATORS_PERMISSIONS_CLASS",
    )

    class Config:
        orm_mode = True


settings = Settings.from_orm(django_settings)
