import requests
import base64
import json
from typing import Dict, Any, Optional, List

class WordPressService:
    def __init__(self, site_url: str, username: str, app_password: str):
        self.site_url = site_url.rstrip('/')
        self.username = username
        self.app_password = app_password
        self.auth_header = self._create_auth_header()
    
    def _create_auth_header(self) -> Dict[str, str]:
        """Create authorization header for WordPress REST API"""
        credentials = f"{self.username}:{self.app_password}"
        token = base64.b64encode(credentials.encode()).decode('utf-8')
        return {'Authorization': f'Basic {token}'}
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the WordPress connection"""
        try:
            response = requests.get(
                f"{self.site_url}/wp-json/wp/v2/users/me",
                headers=self.auth_header,
                timeout=10
            )
            if response.status_code == 200:
                return {'success': True, 'user': response.json()}
            else:
                return {'success': False, 'error': f"Status {response.status_code}: {response.text}"}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def upload_media(self, image_path: str, filename: str) -> Dict[str, Any]:
        """Upload an image to WordPress media library"""
        try:
            with open(image_path, 'rb') as img_file:
                files = {'file': (filename, img_file, 'image/jpeg')}
                response = requests.post(
                    f"{self.site_url}/wp-json/wp/v2/media",
                    headers=self.auth_header,
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 201:
                media = response.json()
                return {
                    'success': True,
                    'media_id': media['id'],
                    'url': media['source_url']
                }
            else:
                return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_post(self, title: str, content: str, status: str = 'publish',
                   featured_media_id: Optional[int] = None,
                   categories: Optional[List[int]] = None,
                   tags: Optional[List[int]] = None) -> Dict[str, Any]:
        """Create a WordPress post"""
        post_data = {
            'title': title,
            'content': content,
            'status': status,
            'format': 'standard',
        }
        
        if featured_media_id:
            post_data['featured_media'] = featured_media_id
        
        if categories:
            post_data['categories'] = categories
        
        if tags:
            post_data['tags'] = tags
        
        try:
            response = requests.post(
                f"{self.site_url}/wp-json/wp/v2/posts",
                headers={**self.auth_header, 'Content-Type': 'application/json'},
                data=json.dumps(post_data),
                timeout=30
            )
            
            if response.status_code == 201:
                post = response.json()
                return {
                    'success': True,
                    'post_id': post['id'],
                    'url': post['link'],
                    'guid': post['guid']['rendered']
                }
            else:
                return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_post(self, post_id: int, **kwargs) -> Dict[str, Any]:
        """Update an existing WordPress post"""
        try:
            response = requests.post(
                f"{self.site_url}/wp-json/wp/v2/posts/{post_id}",
                headers={**self.auth_header, 'Content-Type': 'application/json'},
                data=json.dumps(kwargs),
                timeout=30
            )
            
            if response.status_code == 200:
                return {'success': True, 'post': response.json()}
            else:
                return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}