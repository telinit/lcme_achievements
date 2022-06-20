from django import template


register = template.Library()


@register.filter
def dict_get(dict_, key):
    return dict_[key]