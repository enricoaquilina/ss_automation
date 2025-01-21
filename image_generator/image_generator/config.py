"""Configuration management for image generator"""

import os
from typing import Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

@dataclass
class DatabaseConfig:
    uri: str
    database: str = 'instagram_db'
    timeout_ms: int = 5000
    auth_source: str = 'admin'

@dataclass
class MidjourneyConfig:
    channel_id: str
    oauth_token: str
    api_url: str = 'https://discord.com/api/v9'
    application_id: str = '936929561302675456'
    session_id: str = '379ca7f876ef1793f578d52eb4e5d735'

@dataclass
class Config:
    database: DatabaseConfig
    midjourney: MidjourneyConfig
    log_level: str = 'INFO'

def load_config() -> Config:
    """Load configuration from environment variables"""
    load_dotenv()
    
    return Config(
        database=DatabaseConfig(
            uri=os.getenv('MONGODB_URI', '')
        ),
        midjourney=MidjourneyConfig(
            channel_id=os.getenv('DISCORD_CHANNEL_ID', ''),
            oauth_token=os.getenv('DISCORD_USER_TOKEN', '')
        ),
        log_level=os.getenv('LOG_LEVEL', 'INFO')
    ) 