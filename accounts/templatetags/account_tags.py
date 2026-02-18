from django import template

register = template.Library()


@register.filter
def has_role(user, role_name):
    """Usage in templates: {% if user|has_role:'MERCHANT' %}"""
    if not user.is_authenticated:
        return False
    return user.role == role_name
