from django import forms
from django.forms import ModelForm

from .models import Course


class CourseEdit(ModelForm):
    class Meta:
        model = Course
        fields = '__all__'


class DataImportForm(forms.Form):
    data_type = forms.IntegerField()
    data_content = forms.CharField()
