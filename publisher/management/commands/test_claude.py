from django.core.management.base import BaseCommand
from publisher.claude_service import ClaudeService

class Command(BaseCommand):
    help = 'Test Claude API connection'

    def handle(self, *args, **options):
        self.stdout.write('Testing Claude API connection...')
        
        claude = ClaudeService()
        result = claude.generate_affiliate_content(
            topic="Test Topic",
            prompt="This is a test - generate a short response"
        )
        
        if result['success']:
            self.stdout.write(self.style.SUCCESS('✓ Claude API working!'))
            self.stdout.write(f"Generated title: {result['title']}")
            self.stdout.write(f"Content length: {len(result['content'])} characters")
        else:
            self.stdout.write(self.style.ERROR(f"✗ Failed: {result['error']}"))