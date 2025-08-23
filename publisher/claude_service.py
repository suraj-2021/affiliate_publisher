import anthropic
from django.conf import settings
import re

class ClaudeService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
    
    def generate_affiliate_content(self, topic, prompt=None, affiliate_links=None):
        """Generate long-form affiliate marketing content with E-E-A-T focus"""
        
        # Parse affiliate links
        links = []
        if affiliate_links:
            links = [link.strip() for link in affiliate_links.split('\n') if link.strip()]
        
        # Build the system prompt
        system_prompt = """You are an expert content creator specializing in affiliate marketing blog posts. 
        Create long-form, engaging content that emphasizes:
        - E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness)
        - Personal stories and real-world insights
        - In-depth analysis with comparisons, pros/cons, and references
        - Community engagement through questions and calls for comments
        - Natural SEO optimization without keyword stuffing
        
        Format the content as HTML suitable for WordPress, using proper heading tags (h2, h3), 
        paragraphs, lists, and other semantic HTML. Make the content at least 2000 words."""
        
        # Build the user message
        user_message = f"Write a comprehensive affiliate marketing blog post about: {topic}\n\n"
        
        if prompt:
            user_message += f"Additional context/requirements: {prompt}\n\n"
        
        if links:
            user_message += f"Naturally incorporate these affiliate links throughout the content:\n"
            for i, link in enumerate(links, 1):
                user_message += f"{i}. {link}\n"
            user_message += "\nUse contextual anchor text and integrate them naturally into the content.\n"
        
        user_message += """
        Structure the post with:
        1. Engaging introduction with a personal hook
        2. Multiple detailed sections with subheadings
        3. Product comparisons or analysis (if relevant)
        4. Personal experiences or case studies
        5. Pros and cons lists
        6. Community engagement questions
        7. Strong conclusion with call-to-action
        
        Make it conversational, authoritative, and genuinely helpful to readers.
        """
        
        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            content = response.content[0].text
            
            # Generate a title if not present
            title = self._extract_or_generate_title(content, topic)
            
            # Clean up the content
            content = self._clean_html_content(content)
            
            # Insert affiliate links if they weren't naturally placed
            if links and not all(link in content for link in links):
                content = self._insert_remaining_links(content, links)
            
            return {
                'success': True,
                'title': title,
                'content': content
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_or_generate_title(self, content, topic):
        """Extract title from content or generate one"""
        # Try to find an H1 tag
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.IGNORECASE)
        if h1_match:
            return h1_match.group(1).strip()
        
        # Generate a title based on topic
        return f"The Ultimate Guide to {topic}: Expert Insights and Recommendations"
    
    def _clean_html_content(self, content):
        """Clean and format HTML content"""
        # Remove any H1 tags (WordPress will use post title)
        content = re.sub(r'<h1[^>]*>.*?</h1>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Ensure proper paragraph formatting
        if not content.startswith('<'):
            content = f"<p>{content}</p>"
        
        return content.strip()
    
    def _insert_remaining_links(self, content, links):
        """Insert any remaining affiliate links that weren't naturally placed"""
        for link in links:
            if link not in content:
                # Find a good place to insert the link
                cta_text = f'<p>👉 <a href="{link}" target="_blank" rel="noopener noreferrer">Check out this recommended option</a></p>'
                
                # Insert before the last closing tag or at the end
                if '</div>' in content:
                    content = content.replace('</div>', f'{cta_text}</div>', 1)
                else:
                    content += cta_text
        
        return content