"""Dependency injection container"""

from dependency_injector import containers, providers
from .config import Config, load_config
from .services import DatabaseService, GenerationService

class Container(containers.DeclarativeContainer):
    config = providers.Singleton(load_config)
    
    database_service = providers.Singleton(
        DatabaseService,
        uri=config.provided.database.uri
    )
    
    generation_service = providers.Singleton(
        GenerationService,
        database_service=database_service
    ) 