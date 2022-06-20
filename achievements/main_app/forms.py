from django import forms
from django.forms import ModelForm, FileField

from .models import Course


class CourseEdit(ModelForm):
    class Meta:
        model = Course
        fields = '__all__'
