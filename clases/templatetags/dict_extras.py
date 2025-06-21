# clases/templatetags/dict_extras.py
from django import template

register = template.Library()

@register.filter
def dict_get(diccionario, clave):
    try:
        return diccionario.get(clave)
    except Exception:
        return None


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)




@register.filter(name='add_class')
def add_class(field, css):
    return field.as_widget(attrs={"class": css})
