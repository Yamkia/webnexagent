"""
Instagram OAuth Authentication Module
Handles Instagram login and token management for accessing user data
"""

import os
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

class InstagramOAuth:
    """Handle Instagram OAuth 2.0 authentication flow"""
    
    def __init__(self):
        self.app_id = os.getenv('INSTAGRAM_APP_ID')
        self.app_secret = os.getenv('INSTAGRAM_APP_SECRET')
        self.redirect_uri = os.getenv('INSTAGRAM_REDIRECT_URI', 'http://127.0.0.1:5001/auth/instagram/callback')
        self.base_url = 'https://api.instagram.com'
        self.graph_url = 'https://graph.instagram.com'
        
    def get_authorization_url(self, state=None):
        """
        Generate the Instagram OAuth authorization URL
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            str: Authorization URL to redirect user to
        """
        params = {
            'client_id': self.app_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'user_profile,user_media',
            'response_type': 'code',
        }
        
        if state:
            params['state'] = state
            
        return f"{self.base_url}/oauth/authorize?{urlencode(params)}"
    
    def exchange_code_for_token(self, code):
        """
        Exchange authorization code for access token
        
        Args:
            code: Authorization code from Instagram callback
            
        Returns:
            dict: Token response with access_token and user_id
        """
        url = f"{self.base_url}/oauth/access_token"
        
        data = {
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'code': code
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error exchanging code for token: {e}")
            return None
    
    def get_long_lived_token(self, short_lived_token):
        """
        Exchange short-lived token for long-lived token (60 days)
        
        Args:
            short_lived_token: Short-lived access token
            
        Returns:
            dict: Long-lived token response
        """
        url = f"{self.graph_url}/access_token"
        
        params = {
            'grant_type': 'ig_exchange_token',
            'client_secret': self.app_secret,
            'access_token': short_lived_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting long-lived token: {e}")
            return None
    
    def refresh_token(self, access_token):
        """
        Refresh a long-lived token (extends expiry by 60 days)
        
        Args:
            access_token: Current long-lived token
            
        Returns:
            dict: Refreshed token response
        """
        url = f"{self.graph_url}/refresh_access_token"
        
        params = {
            'grant_type': 'ig_refresh_token',
            'access_token': access_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error refreshing token: {e}")
            return None
    
    def get_user_profile(self, access_token):
        """
        Get user profile information
        
        Args:
            access_token: Instagram access token
            
        Returns:
            dict: User profile data
        """
        url = f"{self.graph_url}/me"
        
        params = {
            'fields': 'id,username,account_type,media_count',
            'access_token': access_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting user profile: {e}")
            return None
    
    def get_user_media(self, access_token, limit=25):
        """
        Get user's media (posts)
        
        Args:
            access_token: Instagram access token
            limit: Number of posts to retrieve
            
        Returns:
            dict: Media data
        """
        url = f"{self.graph_url}/me/media"
        
        params = {
            'fields': 'id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count',
            'access_token': access_token,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting user media: {e}")
            return None
    
    def get_media_insights(self, media_id, access_token):
        """
        Get insights for a specific media item
        
        Args:
            media_id: Instagram media ID
            access_token: Instagram access token
            
        Returns:
            dict: Media insights data
        """
        url = f"{self.graph_url}/{media_id}/insights"
        
        params = {
            'metric': 'engagement,impressions,reach,saved',
            'access_token': access_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting media insights: {e}")
            return None
    
    def calculate_engagement_rate(self, likes, comments, followers):
        """
        Calculate engagement rate
        
        Args:
            likes: Number of likes
            comments: Number of comments
            followers: Number of followers
            
        Returns:
            float: Engagement rate percentage
        """
        if followers == 0:
            return 0.0
        
        total_engagement = likes + comments
        return (total_engagement / followers) * 100
    
    def get_comprehensive_account_data(self, access_token):
        """
        Get comprehensive account data for AI analysis
        
        Args:
            access_token: Instagram access token
            
        Returns:
            dict: Complete account data including profile, media, and calculated metrics
        """
        # Get profile
        profile = self.get_user_profile(access_token)
        if not profile:
            return None
        
        # Get recent media
        media_data = self.get_user_media(access_token, limit=25)
        if not media_data or 'data' not in media_data:
            return None
        
        # Calculate metrics
        total_likes = 0
        total_comments = 0
        post_count = len(media_data['data'])
        
        for post in media_data['data']:
            total_likes += post.get('like_count', 0)
            total_comments += post.get('comments_count', 0)
        
        avg_likes = total_likes / post_count if post_count > 0 else 0
        avg_comments = total_comments / post_count if post_count > 0 else 0
        
        # Note: Instagram Basic Display API doesn't provide follower counts
        # User needs to upgrade to Instagram Graph API (Business/Creator account)
        
        return {
            'username': profile.get('username'),
            'account_type': profile.get('account_type'),
            'media_count': profile.get('media_count'),
            'posts': post_count,
            'avg_likes_per_post': round(avg_likes, 2),
            'avg_comments_per_post': round(avg_comments, 2),
            'total_engagement': total_likes + total_comments,
            'recent_posts': media_data['data'][:10]  # Last 10 posts
        }


# Token storage (in production, use a database)
_token_store = {}

def store_token(user_id, token_data):
    """Store user token data"""
    _token_store[user_id] = {
        'access_token': token_data.get('access_token'),
        'token_type': token_data.get('token_type', 'Bearer'),
        'expires_in': token_data.get('expires_in'),
        'created_at': datetime.now()
    }

def get_token(user_id):
    """Retrieve user token data"""
    return _token_store.get(user_id)

def token_is_valid(user_id):
    """Check if stored token is still valid"""
    token_data = get_token(user_id)
    if not token_data:
        return False
    
    created_at = token_data.get('created_at')
    expires_in = token_data.get('expires_in', 0)
    
    if not created_at:
        return False
    
    expiry_time = created_at + timedelta(seconds=expires_in)
    return datetime.now() < expiry_time
