import pathlib

from relatorio.templates.opendocument import Template
import os

from ..models import *


def generate_for_student(id):
    student = User.objects.get(pk=id)
    educations = Education.objects.filter(student__id=id)
    edu_start_years = map(lambda e: e.start_date.year, educations)
    edu_finish_years = map(lambda e: e.finish_date.year, educations)
    data = {
        'student': student,
        'educations': educations,
        'admission': min( edu_start_years ),
        'graduation': max( edu_finish_years )
    }

    return None
