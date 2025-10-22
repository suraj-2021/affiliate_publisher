import re
from typing import List, Dict, Tuple, Optional
from django.db.models import Q, Count
from .models import PublishedPost, InternalLinkRule, LinkingProfile
import random
from collections import defaultdict

class InternalLinkingService:
    """Service to manage automatic internal linking between posts"""
    
    def __init__(self, user):
        self.user = user
        self.profile, _ = LinkingProfile.objects.get_or_create(user=user)
        self.used_links = defaultdict(int)  # Track usage in current session
    
    def find_relevant_posts(self, topic: str, content: str, 
                           current_post_id: Optional[int] = None,
                           limit: int = None) -> List[PublishedPost]:
        """Find relevant published posts to link to"""
        
        limit = limit or self.profile.max_internal_links
        
        # Extract keywords from topic and content
        keywords = self._extract_keywords(topic, content)
        
        # Build query
        query = Q(status='published') & Q(user=self.user)
        
        # Exclude current post if editing
        if current_post_id:
            query &= ~Q(id=current_post_id)
        
        # Exclude newer posts if preference is set
        if not self.profile.link_to_newer_posts and current_post_id:
            try:
                current_post = PublishedPost.objects.get(id=current_post_id)
                query &= Q(published_at__lt=current_post.published_at)
            except PublishedPost.DoesNotExist:
                pass
        
        # Search by keywords
        keyword_query = Q()
        for keyword in keywords[:10]:  # Use top 10 keywords
            keyword_query |= (
                Q(title__icontains=keyword) |
                Q(topic__icontains=keyword) |
                Q(keywords__icontains=keyword) |
                Q(focus_keyword__iexact=keyword)
            )
        
        posts = PublishedPost.objects.filter(query & keyword_query).distinct()
        
        # Score and sort posts
        scored_posts = []
        for post in posts[:50]:  # Limit initial set for performance
            score = self._calculate_relevance_score(post, keywords, topic)
            scored_posts.append((score, post))
        
        # Sort by relevance
        scored_posts.sort(key=lambda x: x[0], reverse=True)
        
        # Return top matches
        return [post for score, post in scored_posts[:limit]]
    
    def get_linking_suggestions(self, topic: str, content: str) -> Dict[str, any]:
        """Get suggestions for internal links"""
        
        suggestions = {
            'auto_links': [],
            'manual_rules': [],
            'related_posts': [],
            'keywords_found': []
        }
        
        # Find relevant posts
        relevant_posts = self.find_relevant_posts(topic, content)
        suggestions['related_posts'] = [
            {
                'id': post.id,
                'title': post.title,
                'url': post.wordpress_url,
                'topic': post.topic,
                'published': post.published_at.strftime('%Y-%m-%d') if post.published_at else None
            }
            for post in relevant_posts
        ]
        
        # Check for manual linking rules
        rules = InternalLinkRule.objects.filter(
            user=self.user,
            is_active=True
        ).select_related('target_post')
        
        content_lower = content.lower()
        for rule in rules:
            if rule.keyword.lower() in content_lower:
                if rule.target_post.wordpress_url:
                    suggestions['manual_rules'].append({
                        'keyword': rule.keyword,
                        'target_url': rule.target_post.wordpress_url,
                        'target_title': rule.target_post.title,
                        'priority': rule.priority
                    })
        
        # Generate automatic linking suggestions
        keywords = self._extract_keywords(topic, content)
        suggestions['keywords_found'] = keywords[:10]
        
        for post in relevant_posts[:self.profile.max_internal_links]:
            if post.wordpress_url:
                # Find best anchor text
                anchor_texts = self._generate_anchor_texts(post, keywords)
                
                suggestions['auto_links'].append({
                    'post_id': post.id,
                    'url': post.wordpress_url,
                    'title': post.title,
                    'suggested_anchors': anchor_texts,
                    'relevance': 'high' if post in relevant_posts[:3] else 'medium'
                })
        
        return suggestions
    
    def auto_insert_internal_links(self, content: str, topic: str,
                                  current_post_id: Optional[int] = None) -> Tuple[str, List[Dict]]:
        """Automatically insert internal links into content"""
        
        if not self.profile.auto_link_enabled:
            return content, []
        
        # Get relevant posts
        relevant_posts = self.find_relevant_posts(topic, content, current_post_id)
        
        if not relevant_posts:
            return content, []
        
        # Track inserted links
        inserted_links = []
        modified_content = content
        
        # First, apply manual linking rules
        rules = InternalLinkRule.objects.filter(
            user=self.user,
            is_active=True
        ).select_related('target_post').order_by('-priority')
        
        for rule in rules:
            if self.used_links[rule.id] >= rule.max_usage:
                continue
            
            if rule.keyword.lower() in modified_content.lower():
                if rule.target_post.wordpress_url:
                    # Insert link
                    modified_content, inserted = self._insert_link(
                        modified_content,
                        rule.keyword,
                        rule.target_post.wordpress_url,
                        rule.target_post.title
                    )
                    if inserted:
                        self.used_links[rule.id] += 1
                        inserted_links.append({
                            'type': 'rule',
                            'keyword': rule.keyword,
                            'url': rule.target_post.wordpress_url,
                            'title': rule.target_post.title
                        })
        
        # Then, add automatic links for remaining posts
        links_added = len(inserted_links)
        for post in relevant_posts:
            if links_added >= self.profile.max_internal_links:
                break
            
            if not post.wordpress_url:
                continue
            
            # Find suitable anchor text
            anchor_texts = self._generate_anchor_texts(post, self._extract_keywords(topic, content))
            
            for anchor in anchor_texts:
                if anchor.lower() in modified_content.lower():
                    modified_content, inserted = self._insert_link(
                        modified_content,
                        anchor,
                        post.wordpress_url,
                        post.title,
                        vary_anchor=self.profile.vary_anchor_text
                    )
                    if inserted:
                        links_added += 1
                        inserted_links.append({
                            'type': 'auto',
                            'keyword': anchor,
                            'url': post.wordpress_url,
                            'title': post.title
                        })
                        break
            
            if links_added >= self.profile.max_internal_links:
                break
        
        return modified_content, inserted_links
    
    def _extract_keywords(self, topic: str, content: str) -> List[str]:
        """Extract keywords from topic and content"""
        # Simple keyword extraction - can be enhanced with NLP
        text = f"{topic} {content}".lower()
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove common words (simple stop words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were',
                     'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'can', 'could'}
        
        # Extract words
        words = re.findall(r'\b[a-z]+\b', text)
        
        # Count frequency
        word_freq = defaultdict(int)
        for word in words:
            if len(word) > 3 and word not in stop_words:
                word_freq[word] += 1
        
        # Sort by frequency
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, freq in keywords[:20]]
    
    def _calculate_relevance_score(self, post: PublishedPost, 
                                  keywords: List[str], topic: str) -> float:
        """Calculate relevance score between posts"""
        score = 0.0
        
        # Topic similarity
        topic_lower = topic.lower()
        post_topic_lower = post.topic.lower()
        
        if topic_lower == post_topic_lower:
            score += 10
        elif topic_lower in post_topic_lower or post_topic_lower in topic_lower:
            score += 5
        
        # Keyword matching
        post_keywords = post.keywords.lower().split(',') if post.keywords else []
        for keyword in keywords[:10]:
            if keyword in post_keywords:
                score += 2
            if keyword in post.title.lower():
                score += 3
            if keyword == post.focus_keyword.lower():
                score += 5
        
        # Category matching
        if self.profile.prefer_same_category and post.main_category:
            score += 3
        
        # Penalize posts with too many incoming links
        if post.link_to_this_count > 10:
            score *= 0.8
        
        return score
    
    def _generate_anchor_texts(self, post: PublishedPost, 
                              context_keywords: List[str]) -> List[str]:
        """Generate varied anchor texts for a post"""
        anchors = []
        
        if self.profile.use_exact_title:
            anchors.append(post.title)
        
        # Use focus keyword if available
        if post.focus_keyword:
            anchors.append(post.focus_keyword)
        
        # Extract key phrases from title
        title_words = post.title.lower().split()
        if len(title_words) > 3:
            # Use partial title
            anchors.append(' '.join(title_words[:3]))
            anchors.append(' '.join(title_words[-3:]))
        
        # Use topic variations
        if post.topic:
            anchors.append(post.topic.lower())
            
        # Find matching keywords
        for keyword in context_keywords:
            if keyword in post.title.lower() or keyword in post.topic.lower():
                anchors.append(keyword)
        
        # Remove duplicates and return
        return list(dict.fromkeys(anchors))[:5]
    
    def _insert_link(self, content: str, anchor_text: str, url: str, 
                    title: str, vary_anchor: bool = True) -> Tuple[str, bool]:
        """Insert a link into content at the first occurrence of anchor text"""
        
        # Check if anchor text already has a link
        pattern = re.compile(
            rf'<a[^>]*>{re.escape(anchor_text)}</a>',
            re.IGNORECASE
        )
        if pattern.search(content):
            return content, False
        
        # Vary anchor text if requested
        if vary_anchor and random.random() > 0.5:
            # Sometimes use variations
            variations = [
                f"learn more about {anchor_text}",
                f"see our guide on {anchor_text}",
                f"check out {anchor_text}",
                anchor_text
            ]
            anchor_display = random.choice(variations)
        else:
            anchor_display = anchor_text
        
        # Create link HTML
        link_html = f'<a href="{url}" title="{title}" class="internal-link">{anchor_display}</a>'
        
        # Find and replace first occurrence (case-insensitive)
        pattern = re.compile(re.escape(anchor_text), re.IGNORECASE)
        modified_content, count = pattern.subn(link_html, content, count=1)
        
        return modified_content, count > 0
    
    def update_link_statistics(self, post_id: int, linked_posts: List[int]):
        """Update link statistics for posts"""
        # Update link_to_this_count for linked posts
        PublishedPost.objects.filter(id__in=linked_posts).update(
            link_to_this_count=models.F('link_to_this_count') + 1
        )
        
        # Store internal links in the post
        try:
            post = PublishedPost.objects.get(id=post_id)
            post.internal_links = {'linked_to': linked_posts}
            post.save(update_fields=['internal_links'])
        except PublishedPost.DoesNotExist:
            pass
    
    def create_linking_rules_from_post(self, post: PublishedPost):
        """Automatically create linking rules from a published post"""
        if not self.profile.auto_create_rules:
            return
        
        # Extract main keywords from post
        keywords = self._extract_keywords(post.topic, post.title)
        
        # Create rules for top keywords
        for keyword in keywords[:5]:
            if len(keyword) > 4:  # Skip very short words
                InternalLinkRule.objects.get_or_create(
                    user=self.user,
                    keyword=keyword,
                    target_post=post,
                    defaults={'priority': 1, 'max_usage': 3}
                )