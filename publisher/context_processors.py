from .models import ContentStage, UserContentStrategy

def stage_context(request):
    """Add stage data to all templates"""
    if request.user.is_authenticated:
        strategy, _ = UserContentStrategy.objects.get_or_create(user=request.user)
        return {
            'user_strategy': strategy,
            'content_stages': ContentStage.STAGE_CHOICES,
            'current_user_stage': strategy.current_stage,
        }
    return {}