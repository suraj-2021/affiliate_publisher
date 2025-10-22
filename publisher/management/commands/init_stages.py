from django.core.management.base import BaseCommand
from publisher.models import ContentStage
from publisher.claude_service import StagePrompts

class Command(BaseCommand):
    help = 'Initialize content stages with default data'
    
    def handle(self, *args, **options):
        stages_data = [
            {
                'stage_id': 'stage1',
                'name': 'Stage 1 - Foundational Pillars',
                'description': 'Cornerstone content that establishes site authority',
                'word_count_min': 2500,
                'word_count_target': 3000,
                'focus_keywords': 'comprehensive guide, ultimate resource, everything about',
                'content_style': 'authoritative, educational, comprehensive',
                'monetization_focus': 'authority',
                'system_prompt': StagePrompts.STAGE_1_PILLAR
            },
            {
                'stage_id': 'stage2',
                'name': 'Stage 2 - Conversion Content',
                'description': 'Reviews and buying guides that drive revenue',
                'word_count_min': 2000,
                'word_count_target': 2500,
                'focus_keywords': 'best, review, comparison, vs, buying guide',
                'content_style': 'persuasive, balanced, detailed',
                'monetization_focus': 'affiliate',
                'system_prompt': StagePrompts.STAGE_2_CONVERSION
            },
            {
                'stage_id': 'stage3',
                'name': 'Stage 3 - Supporting Content',
                'description': 'Long-tail keywords and specific questions',
                'word_count_min': 1200,
                'word_count_target': 1500,
                'focus_keywords': 'how to, why, what is, fix, troubleshoot',
                'content_style': 'instructional, problem-solving, clear',
                'monetization_focus': 'traffic',
                'system_prompt': StagePrompts.STAGE_3_SUPPORTING
            },
            {
                'stage_id': 'stage4',
                'name': 'Stage 4 - Authority & Community',
                'description': 'Thought leadership and industry analysis',
                'word_count_min': 1500,
                'word_count_target': 2000,
                'focus_keywords': 'future, trends, analysis, opinion, industry',
                'content_style': 'analytical, thought-provoking, engaging',
                'monetization_focus': 'authority',
                'system_prompt': StagePrompts.STAGE_4_AUTHORITY
            },
            {
                'stage_id': 'stage5',
                'name': 'Stage 5 - Ecosystem Expansion',
                'description': 'Niche coverage and new audiences',
                'word_count_min': 1200,
                'word_count_target': 1500,
                'focus_keywords': 'specific, alternative, budget, premium, niche',
                'content_style': 'targeted, specific, diverse',
                'monetization_focus': 'diversified',
                'system_prompt': StagePrompts.STAGE_5_ECOSYSTEM
            },
            {
                'stage_id': 'stage6',
                'name': 'Stage 6 - Brand Building',
                'description': 'Premium content and community building',
                'word_count_min': 1500,
                'word_count_target': 2000,
                'focus_keywords': 'exclusive, premium, community, insider, advanced',
                'content_style': 'personal, brand-focused, premium',
                'monetization_focus': 'brand',
                'system_prompt': StagePrompts.STAGE_6_BRAND
            }
        ]
        
        for stage_data in stages_data:
            stage, created = ContentStage.objects.update_or_create(
                stage_id=stage_data['stage_id'],
                defaults=stage_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created stage: {stage.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Updated stage: {stage.name}')
                )
        
        self.stdout.write(self.style.SUCCESS('Successfully initialized all content stages'))