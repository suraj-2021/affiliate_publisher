import requests
import base64
import json
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime


class WordPressService:
    """Enhanced WordPress REST API integration service"""

    def __init__(self, site_url: str, username: str, app_password: str):
        """Initialize WordPress connection"""
        self.site_url = site_url.rstrip('/')
        self.username = username
        self.app_password = app_password
        self.auth_header = self._create_auth_header()
        self.api_base = f"{self.site_url}/wp-json/wp/v2"

    def _create_auth_header(self) -> Dict[str, str]:
        """Create authorization header for WordPress REST API"""
        credentials = f"{self.username}:{self.app_password}"
        token = base64.b64encode(credentials.encode()).decode('utf-8')
        return {'Authorization': f'Basic {token}'}

    def test_connection(self) -> Dict[str, Any]:
        """Test the WordPress connection and get user info"""
        try:
            response = requests.get(
                f"{self.api_base}/users/me",
                headers=self.auth_header,
                timeout=10
            )

            if response.status_code == 200:
                user_data = response.json()
                return {
                    'success': True,
                    'user': user_data,
                    'capabilities': user_data.get('capabilities', {}),
                    'name': user_data.get('name', 'Unknown')
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'error': 'Authentication failed. Check username and application password.'
                }
            else:
                return {
                    'success': False,
                    'error': f"Connection failed: Status {response.status_code}"
                }
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Connection timeout. Site may be slow or unreachable.'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': 'Cannot connect to site. Check the URL.'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def upload_media_batch(self, images_data):
        """Upload multiple images to WordPress efficiently"""
        results = []

        for img_data in images_data:
            try:
                # Read image file
                with open(img_data['path'], 'rb') as img_file:
                    files = {
                        'file': (
                            img_data['filename'],
                            img_file,
                            'image/jpeg'
                        )
                    }

                    # Prepare metadata
                    data = {
                        'alt_text': img_data.get('alt_text', ''),
                        'caption': img_data.get('caption', ''),
                        'description': img_data.get('description', '')
                    }

                    response = requests.post(
                        f"{self.api_base}/media",
                        headers=self.auth_header,
                        files=files,
                        data=data,
                        timeout=30
                    )

                if response.status_code == 201:
                    media = response.json()
                    results.append({
                        'success': True,
                        'media_id': media['id'],
                        'url': media['source_url'],
                        'wordpress_url': media['link']
                    })
                else:
                    results.append({
                        'success': False,
                        'error': f"Failed to upload {img_data['filename']}"
                    })

            except Exception as e:
                results.append({
                    'success': False,
                    'error': str(e)
                })

        return results

    def create_post_with_images(self, title, content, images, **kwargs):
        """Create post with proper image handling"""

        # Upload all images first
        uploaded_images = []
        featured_media_id = None

        for i, img in enumerate(images):
            result = self.upload_media(
                img['path'],
                img['filename'],
                img.get('alt_text', '')
            )

            if result['success']:
                uploaded_images.append(result)

                # Set first successful upload as featured
                if i == 0 or img.get('is_featured'):
                    featured_media_id = result['media_id']

                # Replace placeholder in content
                placeholder = f"[IMAGE: {img.get('alt_text', '')}]"
                if placeholder in content:
                    img_html = f'<!-- wp:image {{"id":{result["media_id"]},"sizeSlug":"large"}} -->'
                    img_html += f'<figure class="wp-block-image size-large">'
                    img_html += f'<img src="{result["url"]}" alt="{img.get("alt_text", "")}" '
                    img_html += f'class="wp-image-{result["media_id"]}"/>'
                    img_html += f'</figure><!-- /wp:image -->'

                    content = content.replace(placeholder, img_html, 1)

        # Create the post
        return self.create_post(
            title=title,
            content=content,
            featured_media_id=featured_media_id,
            **kwargs
        )

    def create_post(self, title: str, content: str, status: str = 'publish',
                    featured_media_id: Optional[int] = None,
                    categories: Optional[List[int]] = None,
                    tags: Optional[List[int]] = None,
                    excerpt: Optional[str] = None,
                    slug: Optional[str] = None,
                    meta: Optional[Dict] = None,
                    format: str = 'standard') -> Dict[str, Any]:
        """Create a WordPress post with enhanced HTML content support"""

        # Prepare content for WordPress
        formatted_content = self._prepare_content_for_wordpress(content)

        # Build post data
        post_data = {
            'title': title,
            'content': formatted_content,
            'status': status,
            'format': format,
            'comment_status': 'open',
            'ping_status': 'open'
        }

        # Add optional fields
        if featured_media_id:
            post_data['featured_media'] = featured_media_id

        if categories:
            post_data['categories'] = categories

        if tags:
            post_data['tags'] = tags

        if excerpt:
            post_data['excerpt'] = excerpt

        if slug:
            post_data['slug'] = slug

        if meta:
            post_data['meta'] = meta

        try:
            response = requests.post(
                f"{self.api_base}/posts",
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
                    'guid': post['guid']['rendered'],
                    'slug': post['slug'],
                    'status': post['status']
                }
            else:
                error_msg = self._parse_error_response(response)
                return {'success': False, 'error': error_msg}

        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Request timeout. Try again or check server.'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def update_post(self, post_id: int, **kwargs) -> Dict[str, Any]:
        """Update an existing WordPress post"""
        try:
            # Prepare content if provided
            if 'content' in kwargs:
                kwargs['content'] = self._prepare_content_for_wordpress(kwargs['content'])

            response = requests.post(
                f"{self.api_base}/posts/{post_id}",
                headers={**self.auth_header, 'Content-Type': 'application/json'},
                data=json.dumps(kwargs),
                timeout=30
            )

            if response.status_code == 200:
                post = response.json()
                return {
                    'success': True,
                    'post_id': post['id'],
                    'url': post['link'],
                    'modified': post['modified']
                }
            else:
                error_msg = self._parse_error_response(response)
                return {'success': False, 'error': error_msg}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def create_draft(self, title: str, content: str, **kwargs) -> Dict[str, Any]:
        """Create a draft post in WordPress"""
        return self.create_post(title, content, status='draft', **kwargs)

    def get_categories(self) -> Dict[str, Any]:
        """Get all categories from WordPress"""
        try:
            response = requests.get(
                f"{self.api_base}/categories",
                headers=self.auth_header,
                params={'per_page': 100},
                timeout=10
            )

            if response.status_code == 200:
                categories = response.json()
                return {
                    'success': True,
                    'categories': [
                        {'id': cat['id'], 'name': cat['name'], 'slug': cat['slug']}
                        for cat in categories
                    ]
                }
            else:
                return {'success': False, 'error': 'Failed to fetch categories'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_tags(self) -> Dict[str, Any]:
        """Get all tags from WordPress"""
        try:
            response = requests.get(
                f"{self.api_base}/tags",
                headers=self.auth_header,
                params={'per_page': 100},
                timeout=10
            )

            if response.status_code == 200:
                tags = response.json()
                return {
                    'success': True,
                    'tags': [
                        {'id': tag['id'], 'name': tag['name'], 'slug': tag['slug']}
                        for tag in tags
                    ]
                }
            else:
                return {'success': False, 'error': 'Failed to fetch tags'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _prepare_content_for_wordpress(self, content: str) -> str:
        """Prepare and enhance HTML content for WordPress"""

        # Remove any empty paragraphs
        content = re.sub(r'<p>\s*</p>', '', content)

        # Ensure proper paragraph wrapping for plain text lines
        lines = content.split('\n')
        formatted_lines = []
        in_tag = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line starts with HTML tag
            if line.startswith('<'):
                in_tag = True
                formatted_lines.append(line)
            elif line.endswith('>'):
                in_tag = False
                formatted_lines.append(line)
            elif not in_tag and not line.startswith('<'):
                # Wrap plain text in paragraph tags
                formatted_lines.append(f'<p>{line}</p>')
            else:
                formatted_lines.append(line)

        content = '\n'.join(formatted_lines)

        # Convert image placeholders to WordPress blocks
        content = re.sub(
            r'\[IMAGE:\s*(.*?)\]',
            lambda m: self._create_wordpress_image_block(m.group(1)),
            content
        )

        # Add WordPress-specific classes to tables
        content = re.sub(
            r'<table([^>]*)>',
            r'<table\1 class="wp-block-table">',
            content
        )

        # Format blockquotes
        content = re.sub(
            r'<blockquote([^>]*)>',
            r'<blockquote\1 class="wp-block-quote">',
            content
        )

        # Ensure affiliate links have proper attributes
        content = re.sub(
            r'<a\s+([^>]*href=["\'][^"\']*["\'][^>]*)>',
            lambda m: self._format_affiliate_link(m.group(0), m.group(1)),
            content
        )

        # Clean up extra whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content.strip()

    def _create_wordpress_image_block(self, alt_text: str) -> str:
        """Create a WordPress image block HTML"""
        return f''' <!-- wp:image {{"sizeSlug":"large"}} -->
        <figure class="wp-block-image size-large">
        <img alt="{alt_text}" />
        <figcaption>{alt_text}</figcaption>
        </figure>
        <!-- /wp:image --> '''

    def _format_affiliate_link(self, full_tag: str, attributes: str) -> str:
        """Ensure affiliate links have proper attributes"""
        if 'rel=' not in attributes:
            # Add nofollow and noopener for affiliate links
            return full_tag.replace('>', ' rel="nofollow noopener noreferrer">')
        return full_tag

    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type from filename"""
        ext = filename.lower().split('.')[-1]
        mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'svg': 'image/svg+xml'
        }
        return mime_types.get(ext, 'image/jpeg')

    def _parse_error_response(self, response) -> str:
        """Parse error message from WordPress API response"""
        try:
            error_data = response.json()
            if 'message' in error_data:
                return error_data['message']
            elif 'code' in error_data:
                return f"Error: {error_data.get('code', 'Unknown')}"
            else:
                return f"Status {response.status_code}: {response.text[:200]}"
        except:
            return f"Status {response.status_code}: {response.text[:200]}"

    def schedule_post(self, title: str, content: str,
                      publish_date: datetime, **kwargs) -> Dict[str, Any]:
        """Schedule a post for future publication"""
        post_data = {
            'status': 'future',
            'date': publish_date.isoformat()
        }
        post_data.update(kwargs)
        return self.create_post(title, content, **post_data)

    def bulk_upload_media(self, image_paths: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """Bulk upload multiple images"""
        results = []
        for path, filename in image_paths:
            result = self.upload_media(path, filename)
            results.append(result)
        return results
    def upload_media(self, path: str, filename: str, alt_text: str = "") -> Dict[str, Any]:
        """Upload a single image to WordPress"""
        try:
            with open(path, 'rb') as img_file:
                files = {
                    'file': (filename, img_file, self._get_mime_type(filename))
                }
                data = {'alt_text': alt_text}
                response = requests.post(
                    f"{self.api_base}/media",
                    headers=self.auth_header,
                    files=files,
                    data=data,
                    timeout=30
                )
            if response.status_code == 201:
                media = response.json()
                return {
                    'success': True,
                    'media_id': media['id'],
                    'url': media['source_url'],
                    'wordpress_url': media['link']
                }
            else:
                return {'success': False, 'error': f"Failed with status {response.status_code}"}
        except Exception as e:
            return {'success': False, 'error': str(e)}
