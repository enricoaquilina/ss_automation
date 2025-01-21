"""Instagram token management"""
import os
import json
import httpx
from datetime import datetime, timedelta
from typing import Optional

class InstagramTokenManager:
    def __init__(self):
        self.token_file = "instagram_token.json"
        self.app_id = os.getenv("INSTAGRAM_APP_ID")
        self.app_secret = os.getenv("INSTAGRAM_APP_SECRET")
        self.long_token = os.getenv("INSTAGRAM_LONG_TOKEN")

    async def refresh_long_lived_token(self) -> Optional[str]:
        """Refresh long-lived token before expiry (around day 50)"""
        try:
            url = f"https://graph.facebook.com/v21.0/oauth/access_token"
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "access_token": self.long_token,
                "fb_exchange_token": self.long_token
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                data = response.json()

                if 'access_token' in data:
                    return self._save_token(data)
                return None

        except Exception as e:
            print(f"Error refreshing long-lived token: {e}")
            return None

    def _save_token(self, data: dict) -> str:
        """Save token data to file"""
        new_token = data['access_token']
        expires_at = datetime.now() + timedelta(seconds=int(data['expires_in']))
        
        token_data = {
            'access_token': new_token,
            'expires_at': expires_at.isoformat()
        }
        with open(self.token_file, 'w') as f:
            json.dump(token_data, f)
        
        os.environ['INSTAGRAM_LONG_TOKEN'] = new_token
        self.long_token = new_token
        
        return new_token

    async def get_valid_token(self) -> Optional[str]:
        """Get current token, refresh if needed"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    expires_at = datetime.fromisoformat(data['expires_at'])
                    
                    if expires_at - timedelta(days=10) <= datetime.now():
                        return await self.refresh_long_lived_token()
                    return data['access_token']
                    
            return await self.refresh_long_lived_token()
            
        except Exception as e:
            print(f"Error getting valid token: {e}")
            return None 