import os
import requests
from typing import Optional, Dict, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class InstagramGraphAPI:
    """
    Instagram Graph API Integration
    Connects to real Instagram Business accounts via Meta's Graph API.
    """
    
    def __init__(self):
        self.app_id = os.getenv('INSTAGRAM_APP_ID')
        self.app_secret = os.getenv('INSTAGRAM_APP_SECRET')
        self.access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.business_account_id = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
        self.base_url = 'https://graph.facebook.com/v18.0'
        
    def is_configured(self) -> bool:
        """Check if API credentials are properly configured."""
        return all([
            self.access_token,
            self.business_account_id
        ])
    
    def get_account_info(self) -> Dict:
        """
        Get Instagram Business account information.
        
        Returns:
            dict: Account information including username, follower count, etc.
        """
        if not self.is_configured():
            return {
                'error': 'Instagram API not configured. Please set up your credentials.',
                'setup_guide': 'See INSTAGRAM_API_SETUP.md for instructions'
            }
        
        try:
            url = f"{self.base_url}/{self.business_account_id}"
            params = {
                'fields': 'username,name,biography,followers_count,follows_count,media_count,profile_picture_url',
                'access_token': self.access_token
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Transform to match our existing format
            return {
                'username': f"@{data.get('username', 'unknown')}",
                'name': data.get('name', ''),
                'account_type': 'Business',
                'followers': data.get('followers_count', 0),
                'following': data.get('follows_count', 0),
                'posts': data.get('media_count', 0),
                'bio': data.get('biography', ''),
                'profile_picture': data.get('profile_picture_url', ''),
                'verified': False,  # Graph API doesn't provide this in basic info
                'last_updated': datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            return {'error': f'Failed to fetch account info: {str(e)}'}
    
    def get_insights(self, metrics: List[str] = None, period: str = 'day') -> Dict:
        """
        Get Instagram account insights (analytics).
        
        Args:
            metrics: List of metrics to fetch. Defaults to common metrics.
            period: Time period ('day', 'week', 'days_28')
        
        Returns:
            dict: Account insights data
        """
        if not self.is_configured():
            return {'error': 'Instagram API not configured'}
        
        if metrics is None:
            metrics = [
                'impressions',
                'reach',
                'profile_views',
                'follower_count'
            ]
        
        try:
            url = f"{self.base_url}/{self.business_account_id}/insights"
            params = {
                'metric': ','.join(metrics),
                'period': period,
                'access_token': self.access_token
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Transform insights data
            insights = {}
            for item in data.get('data', []):
                metric_name = item.get('name')
                values = item.get('values', [])
                if values:
                    insights[metric_name] = values[-1].get('value', 0)
            
            return {
                'period': period,
                'insights': insights,
                'fetched_at': datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            return {'error': f'Failed to fetch insights: {str(e)}'}
    
    def get_recent_media(self, limit: int = 10) -> List[Dict]:
        """
        Get recent media posts from the account.
        
        Args:
            limit: Number of posts to retrieve (max 25)
        
        Returns:
            list: List of media posts with engagement data
        """
        if not self.is_configured():
            return [{'error': 'Instagram API not configured'}]
        
        try:
            # First, get media IDs
            url = f"{self.base_url}/{self.business_account_id}/media"
            params = {
                'fields': 'id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count',
                'limit': min(limit, 25),
                'access_token': self.access_token
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            media_list = []
            for item in data.get('data', []):
                media_list.append({
                    'id': item.get('id'),
                    'caption': item.get('caption', '')[:100] + '...' if len(item.get('caption', '')) > 100 else item.get('caption', ''),
                    'media_type': item.get('media_type'),
                    'media_url': item.get('media_url'),
                    'permalink': item.get('permalink'),
                    'timestamp': item.get('timestamp'),
                    'likes': item.get('like_count', 0),
                    'comments': item.get('comments_count', 0),
                    'engagement_rate': self._calculate_engagement_rate(
                        item.get('like_count', 0),
                        item.get('comments_count', 0)
                    )
                })
            
            return media_list
            
        except requests.exceptions.RequestException as e:
            return [{'error': f'Failed to fetch media: {str(e)}'}]
    
    def get_follower_growth(self, days: int = 30) -> Dict:
        """
        Get follower growth over time.
        
        Note: This requires historical data access which may need app review.
        For basic accounts, we can only get current follower count.
        
        Args:
            days: Number of days to look back
        
        Returns:
            dict: Follower growth data
        """
        if not self.is_configured():
            return {'error': 'Instagram API not configured'}
        
        try:
            # Get current follower count
            current_info = self.get_account_info()
            
            if 'error' in current_info:
                return current_info
            
            return {
                'current_followers': current_info.get('followers', 0),
                'period_days': days,
                'note': 'Historical growth data requires Instagram Insights API with app review approval',
                'fetched_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': f'Failed to fetch follower growth: {str(e)}'}
    
    def _calculate_engagement_rate(self, likes: int, comments: int, followers: int = None) -> float:
        """Calculate engagement rate for a post."""
        if followers is None:
            # Use current followers if not provided
            account_info = self.get_account_info()
            followers = account_info.get('followers', 1)
        
        if followers == 0:
            return 0.0
        
        engagement = likes + comments
        return round((engagement / followers) * 100, 2)
    
    def publish_photo(self, image_url: str, caption: str) -> Dict:
        """
        Publish a photo to Instagram.
        
        Args:
            image_url: URL of the image (must be publicly accessible)
            caption: Post caption
        
        Returns:
            dict: Publishing result with media ID
        """
        if not self.is_configured():
            return {'error': 'Instagram API not configured'}
        
        try:
            # Step 1: Create media container
            url = f"{self.base_url}/{self.business_account_id}/media"
            params = {
                'image_url': image_url,
                'caption': caption,
                'access_token': self.access_token
            }
            
            response = requests.post(url, params=params, timeout=10)
            response.raise_for_status()
            creation_data = response.json()
            
            container_id = creation_data.get('id')
            
            # Step 2: Publish the media container
            publish_url = f"{self.base_url}/{self.business_account_id}/media_publish"
            publish_params = {
                'creation_id': container_id,
                'access_token': self.access_token
            }
            
            publish_response = requests.post(publish_url, params=publish_params, timeout=10)
            publish_response.raise_for_status()
            publish_data = publish_response.json()
            
            return {
                'success': True,
                'media_id': publish_data.get('id'),
                'message': 'Photo published successfully!',
                'published_at': datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Failed to publish photo: {str(e)}'
            }


# Create a global instance
instagram_api = InstagramGraphAPI()
