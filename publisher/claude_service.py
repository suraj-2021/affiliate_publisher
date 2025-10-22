import anthropic
from django.conf import settings
import re
from collections import Counter

class StagePrompts:
    """Stage-specific prompt templates - original detailed versions"""
    
    STAGE_1_PILLAR = """You are an expert affiliate content creator specializing in FOUNDATIONAL PILLAR content.

    STAGE 1 OBJECTIVES:
    - Create authoritative cornerstone content that **establishes trust and expertise** in the niche.
    - Cover broad, evergreen topics with encyclopedic depth (4000–5000 words).
    - Answer the most common and high-value questions comprehensively.
    - Serve as the **hub for internal linking** across related supporting and conversion content.
    - Build long-term credibility so the article becomes the **reference point for years**.

    CONTENT CHARACTERISTICS:
    - Highly comprehensive, entity-rich coverage spanning multiple subtopics.
    - Balances **breadth (overview)** and **depth (expert insights, data, FAQs)**.
    - Strong EEAT signals: cite credible sources, include expert quotes, show authoritativeness.
    - Transparent tone: prioritize education and knowledge before commercial intent.
    - SEO-first but user-driven: semantic variation, synonyms, and related questions woven naturally.
    - Designed to attract backlinks, social shares, and citations.

    STRUCTURE:
    - Use H2 and H3 subheadings for clear organization (no H1).
    - Deep dives into each major aspect of the topic.
    - Include comparison tables, charts, diagrams, and visual aids where useful.
    - Expert quotes, data-driven evidence, and industry references.
    - Comprehensive FAQ section (8–12 FAQs).
    - Links to both internal (supporting articles, product reviews) and external authoritative resources.

    IMPORTANT:
    - Do not include a Table of Contents — this will be inserted automatically.
    - Content must be **evergreen, trustworthy, and reference-worthy**."""

    STAGE_2_CONVERSION = """You are an expert affiliate content creator specializing in CONVERSION-FOCUSED content.

    STAGE 2 OBJECTIVES:
    - Create persuasive, user-first content that **helps readers make purchase decisions confidently**.
    - Balance **trustworthiness with gentle persuasion** — the goal is conversions without hype.
    - Provide honest, detailed product reviews and comparisons.
    - Drive affiliate revenue through **transparent, helpful recommendations**.

    CONTENT CHARACTERISTICS:
    - Detailed breakdown of each product/service: features, usability, and real-world scenarios.
    - Balanced pros and cons — avoid exaggerated claims, focus on authenticity.
    - Comparative analysis highlighting **which product fits which type of user**.
    - Price-to-value assessment with clarity on what justifies the cost.
    - Clear “Best for…” scenarios (e.g., best for students, best for professionals).
    - Transparent affiliate disclosure integrated naturally into the narrative.
    - SEO-friendly: use structured headings for product reviews, “vs” comparisons, and key differentiators.

    STRUCTURE:
    - Use H2 and H3 for each product section (no H1).
    - Include **comparison tables** summarizing differences at a glance.
    - Add user testimonials, case studies, or aggregated review snippets for social proof.
    - Provide clear recommendations by use case (who should buy what).
    - Mention active deals, discounts, or promotions where relevant.
    - Strong but ethical CTAs encouraging the reader to click affiliate links.

    IMPORTANT:
    - Do not add a “Verdict box” or summary at the top — this will be inserted automatically.
    - Maintain **trust and authenticity** — credibility comes before conversions."""

    STAGE_3_SUPPORTING = """You are an expert content creator specializing in SUPPORTING/CLUSTER content.

    STAGE 3 OBJECTIVES:
    - Target long-tail queries and highly specific user questions.
    - Drive consistent organic traffic by **capturing informational and how-to intent**.
    - Support pillar content by creating natural opportunities for internal linking.
    - Provide actionable, **step-by-step solutions** to specific problems.

    CONTENT CHARACTERISTICS:
    - Problem-solving and intent-focused: every section must provide **direct answers**.
    - Use a tutorial/guide style with numbered steps where appropriate.
    - Clear, concise, and actionable — avoid fluff.
    - Quick intent satisfaction: answers should be scannable and snippet-friendly.
    - Natural bridges to pillar or conversion content without sounding forced.
    - SEO-rich: include FAQs, synonyms, and entity-based variations.

    STRUCTURE:
    - Start with a **direct answer in the opening paragraph** (featured snippet style).
    - Use H2 and H3 headings for clarity (no H1).
    - Provide step-by-step breakdowns where relevant.
    - Add visuals, code snippets, screenshots, or short examples if helpful.
    - Short FAQ section (3–5 questions) addressing related queries.
    - Link naturally to relevant pillar content.

    IMPORTANT:
    - The first paragraph must **directly answer the main query** — do not use a separate answer box.
    - Prioritize **clarity, intent-satisfaction, and usability** over length."""

    STAGE_4_AUTHORITY = """You are an expert content creator specializing in AUTHORITY & COMMUNITY content.

STAGE 4 OBJECTIVES:
- Build **thought leadership** by exploring trends, industry shifts, and future directions.
- Strengthen credibility through **original insights, expert commentary, and unique perspectives**.
- Spark community discussion and encourage sharing.
- Generate backlinks and mentions by providing **data-rich, unique analysis**.

CONTENT CHARACTERISTICS:
- Covers emerging industry trends, innovations, and predictions.
- Balanced perspective: include multiple viewpoints, not just one.
- Backed by data: reference studies, reports, or case examples.
- Offers **unique insights** — analysis should go beyond surface-level commentary.
- Controversial or discussion-worthy angles to prompt reader engagement.
- SEO-driven: optimized for trend searches, “future of X,” and thought-leadership queries.

STRUCTURE:
- Strong, thought-provoking introduction.
- Use H2 and H3 headings for sections (no H1).
- Present supporting data, case studies, or expert interviews.
- Analyze multiple viewpoints and their implications.
- Explore future scenarios and predictions.
- End with **share-worthy conclusions** that readers want to reference.

IMPORTANT:
- Focus on insights and expert analysis — **discussion prompts will be inserted automatically** later.
- Avoid “news reporting” tone — emphasize **analysis, credibility, and unique perspective**."""

    STAGE_5_ECOSYSTEM = """You are an expert content creator specializing in ECOSYSTEM EXPANSION content.

STAGE 5 OBJECTIVES:
- Achieve **comprehensive topical authority** by covering every long-tail keyword in the niche.
- Diversify monetization strategies beyond affiliate links (courses, downloads, tools).
- Reach and engage **new audience segments**.
- Strengthen topical clusters and interlinking.

CONTENT CHARACTERISTICS:
- Highly specific, niche-subtopic coverage (long-tail SEO).
- Builds semantic depth and **topic cluster completeness**.
- Naturally integrates alternative monetization (lead magnets, premium tools, memberships).
- Promotes other content pieces across the site.
- Encourages UGC (user tips, reviews, or comments) where possible.
- Flexible format: lists, tutorials, calculators, mini-guides.

STRUCTURE:
- Use scannable, digestible formats (lists, quick guides).
- Clear H2/H3 hierarchy (no H1).
- Provide multiple monetization touchpoints (e.g., course mentions, tool recommendations).
- Include quick examples, templates, or actionable checklists.
- Cross-promote related guides, pillar posts, or premium products.

IMPORTANT:
- Do not handle email capture directly — it will be automated.
- Focus on **depth of topic coverage** and ecosystem-level content expansion."""

    
    STAGE_6_BRAND = """You are an expert content creator specializing in BRAND BUILDING & FUNNEL content.
    
    STAGE 6 OBJECTIVES:
    - Build email lists and owned audiences
    - Create premium content and products
    - Establish brand partnerships
    - Develop recurring revenue streams
    
    CONTENT CHARACTERISTICS:
    - Premium, exclusive insights
    - Behind-the-scenes content
    - Brand storytelling
    - Community success stories
    - Partnership announcements
    - Product launches and updates
    
    STRUCTURE:
    - Personal, brand-voice heavy
    - Use H2 and H3 headings for organization (no H1 tags)
    - Premium content teasers
    - Community highlights
    - Partnership showcases
    - Clear funnel progression
    
    IMPORTANT: Focus on content and storytelling - conversion elements will be added during post-processing."""
    
    @classmethod
    def get_stage_prompt(cls, stage):
        """Get the appropriate prompt for a content stage"""
        prompts = {
            'stage1': cls.STAGE_1_PILLAR,
            'stage2': cls.STAGE_2_CONVERSION,
            'stage3': cls.STAGE_3_SUPPORTING,
            'stage4': cls.STAGE_4_AUTHORITY,
            'stage5': cls.STAGE_5_ECOSYSTEM,
            'stage6': cls.STAGE_6_BRAND,
        }
        return prompts.get(stage, cls.STAGE_1_PILLAR)

class ClaudeService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
    
    def generate_affiliate_content(self, topic, prompt=None, affiliate_links=None, 
                                  content_stage='stage1', word_count=4000,
                                  include_internal_links=True, internal_links=None):
        """Generate content based on the specified stage"""
        
        # Get stage-specific system prompt
        stage_prompt = StagePrompts.get_stage_prompt(content_stage)
        
        # Base expert writer prompt
        base_prompt = base_prompt = """You are an **expert affiliate content creator and professional writer**. 
Your writing must embody **Google's EEAT principles**: expertise, experience, authoritativeness, and trustworthiness. 
Showcase first-hand knowledge, credible references, and authentic insights. 

Tone: warm, authoritative, and engaging —like a trusted advisor who blends deep expertise with relatable personal experience.

SEO / UX Guidelines:
- Write to fully satisfy search intent (informational, commercial, or transactional).
- Use semantic depth: related entities, synonyms, and variations of the main topic.
- Always prioritize clarity, readability, and user trust over keyword stuffing.
- Be transparent: where products or services are recommended, explain selection criteria and disclose affiliate nature naturally.
- Provide real-world examples, comparisons, and context to build trust.

Formatting:

- Output clean, semantic HTML ready for WordPress publishing.
- Use proper heading hierarchy (H2 → H3 → H4) for structure.
- Do not use H1 tags (the title will be handled separately).
- Use bulleted lists, tables, blockquotes, and FAQs where helpful to improve scanability.
"""

        
        # Get stage-specific word count
        stage_word_counts = {
            'stage1': max(4000, word_count),
            'stage2': max(2500, word_count),
            'stage3': max(1500, word_count),
            'stage4': max(2000, word_count),
            'stage5': max(1500, word_count),
            'stage6': max(2000, word_count),
        }
        
        target_words = stage_word_counts.get(content_stage, word_count)
        
        # Combine prompts
        system_prompt = f"{base_prompt}\n\n{stage_prompt}\n\nTarget: {target_words} words minimum."
        
        # Prepare affiliate links
        links = []
        if affiliate_links:
            links = [link.strip() for link in affiliate_links.split('\n') if link.strip()]
        
        # Build user message
        user_message = self._build_user_message(
            topic, prompt, links, content_stage, internal_links, target_words
        )
        
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10000,
                temperature=0.6,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            content = response.content[0].text
            
            # Apply stage-specific post-processing ONLY if elements don't exist
            formatted_content = self._format_content_by_stage(content, content_stage)
            
            # Extract metadata
            title = self._extract_or_generate_title(formatted_content, topic)
            keywords = self._extract_keywords_from_content(formatted_content)
            
            return {
                'success': True,
                'title': title,
                'content': formatted_content,
                'keywords': keywords,
                'word_count': len(formatted_content.split()),
                'stage': content_stage
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _build_user_message(self, topic, prompt, links, stage, internal_links, word_count):
        """Build stage-specific user message"""
        
        stage_instructions = {
            'stage1': """Create a comprehensive PILLAR POST about: {topic}
            
            Requirements:
            - Minimum {word_count} words of in-depth, authoritative content
            - Cover ALL major aspects of the topic
            - Include extensive research and data
            - Create 10+ detailed sections
            - Design for long-term reference value
            - Focus on education over sales
            """,
            
            'stage2': """Create a detailed PRODUCT REVIEW/BUYING GUIDE about: {topic}
            
            Requirements:
            - Detailed analysis of top products/services
            - Honest pros and cons for each option
            - Comparison tables with key features
            - Price analysis and value propositions
            - Clear recommendations by use case
            - Strong affiliate link integration
            """,
            
            'stage3': """Create a SUPPORTING ARTICLE answering specific questions about: {topic}
            
            Requirements:
            - Direct answer to the query in the first paragraph
            - Step-by-step instructions if applicable
            - Practical, actionable advice
            - Link to related pillar content
            - Focus on solving one specific problem
            """,
            
            'stage4': """Create an AUTHORITY/THOUGHT LEADERSHIP piece about: {topic}
            
            Requirements:
            - Industry trends and analysis
            - Unique perspectives and opinions
            - Data-driven insights
            - Future predictions
            - Encourage discussion and debate
            - Build credibility and expertise
            """,
            
            'stage5': """Create an ECOSYSTEM/NICHE EXPANSION article about: {topic}
            
            Requirements:
            - Cover specific long-tail topics
            - Multiple monetization opportunities
            - Cross-promotion of products/services
            - Build comprehensive coverage
            - Target new audience segments
            """,
            
            'stage6': """Create a BRAND/FUNNEL BUILDING piece about: {topic}
            
            Requirements:
            - Personal brand storytelling
            - Email capture opportunities
            - Premium content teasers
            - Community engagement focus
            - Funnel progression elements
            - Exclusive insights and value
            """
        }
        
        message = stage_instructions.get(stage, stage_instructions['stage1']).format(
            topic=topic, 
            word_count=word_count
        )
        
        if prompt:
            message += f"\n\nAdditional instructions: {prompt}"
        
        if links:
            message += f"\n\nIntegrate these affiliate links naturally:\n"
            for link in links[:5]:  # Limit to 5 links
                message += f"- {link}\n"
        
        if internal_links:
            message += f"\n\nReference these related articles where relevant:\n"
            for link in internal_links[:5]:  # Limit to 5 internal links
                message += f"- {link['title']}\n"
        
        message += "\n\nFormat as clean, semantic HTML ready for WordPress publishing."
        
        return message
    
    def _format_content_by_stage(self, content, stage):
        """Apply stage-specific formatting only if not already present"""
        
        # Check if elements already exist before adding them
        content_lower = content.lower()
        
        # Only add enhancements if they don't already exist
        if stage in ['stage1', 'stage2'] and 'table-of-contents' not in content_lower:
            content = self._add_comprehensive_toc(content)
        
        if stage == 'stage2' and 'quick-verdict' not in content_lower and 'verdict' not in content_lower:
            content = self._add_quick_verdict_box(content)
        
        if stage == 'stage3' and 'quick-answer' not in content_lower:
            # Only add if first paragraph isn't already a direct answer
            if not self._has_direct_answer_start(content):
                content = self._add_quick_answer_box(content)
        
        if stage == 'stage4' and 'discussion-prompt' not in content_lower:
            content = self._add_discussion_prompts(content)
        
        if stage in ['stage5', 'stage6'] and 'email-capture' not in content_lower:
            content = self._add_conversion_elements(content)
        
        return self._clean_html_content(content)
    
    def _has_direct_answer_start(self, content):
        """Check if content already starts with a direct answer"""
        first_p_match = re.search(r'<p>(.*?)</p>', content, re.DOTALL)
        if first_p_match:
            first_para = first_p_match.group(1).lower()
            # Check for direct answer indicators
            answer_indicators = ['the answer is', 'simply put', 'in short', 'to answer', 'directly']
            return any(indicator in first_para for indicator in answer_indicators)
        return False
    
    def _add_comprehensive_toc(self, content):
        """Add a comprehensive table of contents for pillar content"""
        headings = re.findall(r'<h([23])[^>]*>(.*?)</h[23]>', content, re.IGNORECASE)
        
        if len(headings) > 3:
            toc = '<div class="table-of-contents" style="background:#f8f9fa;padding:20px;border:1px solid #e9ecef;border-radius:5px;margin:20px 0;">\n'
            toc += '<h2>Table of Contents</h2>\n<ul style="list-style-type:none;padding-left:0;">\n'
            
            # Build TOC and modify headings to include anchors
            for i, (level, heading) in enumerate(headings):
                clean_heading = re.sub(r'<[^>]+>', '', heading).strip()
                anchor = f"section-{i+1}"
                indent = "margin-left:20px;" if level == '3' else ""
                toc += f'<li style="{indent}"><a href="#{anchor}">{clean_heading}</a></li>\n'
                
                # Add anchor ID to the actual heading in content
                original_pattern = f'<h{level}[^>]*>{re.escape(heading)}</h{level}>'
                replacement = f'<h{level} id="{anchor}">{heading}</h{level}>'
                content = re.sub(original_pattern, replacement, content, count=1, flags=re.IGNORECASE)
            
            toc += '</ul>\n</div>\n\n'
            
            # Insert TOC after first paragraph
            first_p_end = content.find('</p>')
            if first_p_end > 0:
                content = content[:first_p_end+4] + toc + content[first_p_end+4:]
        
        return content
    
    def _add_quick_verdict_box(self, content):
        """Add quick verdict box for conversion content"""
        verdict_html = """
        <div class="quick-verdict-box" style="background:#f0f8ff;padding:20px;border-left:4px solid #0073aa;margin:20px 0;">
            <h3 style="color:#0073aa;margin-top:0;">Quick Verdict</h3>
            <p><strong>Our Top Pick:</strong> Based on our analysis, we recommend checking the options above for the best balance of features and value.</p>
        </div>
        """
        
        # Add after first paragraph if not already present
        first_p_end = content.find('</p>')
        if first_p_end > 0:
            content = content[:first_p_end+4] + verdict_html + content[first_p_end+4:]
        
        return content
    
    def _add_quick_answer_box(self, content):
        """Add quick answer box for supporting content"""
        # Extract first paragraph as the quick answer
        first_p_match = re.search(r'<p>(.*?)</p>', content, re.DOTALL)
        if first_p_match:
            first_paragraph = first_p_match.group(1)
            answer_box = f"""
            <div class="quick-answer" style="background:#e8f5e9;padding:15px;border-radius:5px;margin:20px 0;border-left:4px solid #28a745;">
                <h3 style="color:#28a745;margin-top:0;">Quick Answer</h3>
                <p>{first_paragraph}</p>
            </div>
            """
            
            # Replace first paragraph with answer box
            content = content.replace(first_p_match.group(0), answer_box, 1)
        
        return content
    
    def _add_discussion_prompts(self, content):
        """Add discussion prompts for authority content"""
        discussion_prompt = """
        <div class="discussion-prompt" style="background:#fff3cd;padding:20px;border:2px dashed #ffc107;border-radius:5px;margin:30px 0;">
            <h3 style="color:#856404;margin-top:0;">What's Your Take?</h3>
            <p>What do you think about these trends? Have you noticed similar changes in your experience?</p>
            <p><strong>Share your thoughts in the comments below – we'd love to hear your perspective!</strong></p>
        </div>
        """
        
        # Add before the last paragraph
        content = content.rstrip()
        if content.endswith('</p>'):
            last_p_start = content.rfind('<p>')
            if last_p_start > 0:
                content = content[:last_p_start] + discussion_prompt + content[last_p_start:]
        
        return content
    
    def _add_conversion_elements(self, content):
        """Add conversion elements for ecosystem and brand content"""
        conversion_box = """
        <div class="email-capture" style="background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);color:white;padding:30px;border-radius:10px;margin:30px 0;text-align:center;">
            <h3 style="color:white;margin-top:0;">Want More Insider Tips?</h3>
            <p>Join our community for exclusive guides, deals, and expert insights delivered to your inbox.</p>
            <p><em>[Newsletter signup form goes here]</em></p>
        </div>
        """
        
        # Find a good insertion point (around 60% through content)
        insertion_point = int(len(content) * 0.6)
        next_p_end = content.find('</p>', insertion_point)
        if next_p_end > 0:
            content = content[:next_p_end+4] + conversion_box + content[next_p_end+4:]
        
        return content
    
    def _clean_html_content(self, content):
        """Clean and format HTML content"""
        # Remove any H1 tags that might have been generated
        content = re.sub(r'<h1[^>]*>.*?</h1>', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Add WordPress-friendly classes
        content = content.replace('<table>', '<table class="wp-block-table">')
        content = content.replace('<blockquote>', '<blockquote class="wp-block-quote">')
        
        # Clean up excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'<p>\s*</p>', '', content)  # Remove empty paragraphs
        
        return content.strip()
    
    def _extract_keywords_from_content(self, content):
        """Extract keywords for SEO and internal linking"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', content)
        
        # Extract meaningful words (4+ characters)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        
        # Count frequency
        word_freq = Counter(words)
        
        # Filter out common stop words
        stop_words = {
            'this', 'that', 'with', 'from', 'have', 'more', 'about', 'which', 
            'their', 'will', 'been', 'were', 'said', 'each', 'them', 'than',
            'many', 'some', 'time', 'very', 'when', 'much', 'such', 'most',
            'also', 'like', 'just', 'into', 'only', 'over', 'back', 'after',
            'here', 'well', 'what', 'make', 'come', 'know', 'take'
        }
        
        # Get relevant keywords
        keywords = [
            word for word, freq in word_freq.most_common(20) 
            if word not in stop_words and freq > 2 and len(word) > 4
        ]
        
        return ','.join(keywords[:10])
    
    def _extract_or_generate_title(self, content, topic):
        """Extract title from content or generate from topic"""
        # First try to find an H2 at the beginning (common pattern)
        h2_match = re.search(r'<h2[^>]*>(.*?)</h2>', content, re.IGNORECASE)
        if h2_match:
            title = re.sub(r'<[^>]+>', '', h2_match.group(1)).strip()
            if len(title) > 10 and len(title) < 70:  # Reasonable title length
                return title
        
        # Fallback to topic with some enhancement
        if len(topic) < 40:
            return f"Complete Guide to {topic}"
        else:
            return topic[:60] + "..." if len(topic) > 60 else topic