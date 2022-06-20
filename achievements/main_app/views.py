from io import BytesIO

from django.core import serializers
from django.db import transaction
from django.db.models import F, Count
from django.db.models.functions import ExtractYear
from django.http import HttpResponse, FileResponse, HttpResponseBadRequest
from django.shortcuts import render
import csv

# Create your views here.
from django.template import loader

from .forms import CourseEdit
from .models import User, Education, Course, CourseParticipation, SeminarParticipation, ProjectParticipation, \
    OlympiadParticipation, Project, Olympiad, Seminar
from .reports.student_report import generate_document_for_many_students, document_to_odt_data, \
    generate_document_for_student, odt_data_to_pdf_reader
from .util.data_import import *
from .util.util import group_by_type, add_to_dict_multival_set


def append_json_data(rec):
    rec.data = serializers.serialize('json', [rec])
    return rec


def p404(request, exception):
    return render(request, 'errors/404.html')


def index(request):
    stats = {
        'students': Education.objects.values('student__id').distinct().count(),
        'courses': Course.objects.values('id').distinct().count(),
        'projects': Project.objects.values('id').distinct().count(),
        'olympiads': Olympiad.objects.values('id').distinct().count(),
        'seminars': Seminar.objects.values('id').distinct().count(),
    }
    return render(request, 'index.html', {'stats': stats})


def students(request):
    # edus = Education.objects.all().annotate(scount=Count('student_id'))
    users = User.objects.filter(education__isnull=False).distinct()
    departments = Department.objects.all()
    students = []
    for u in users:
        students.append({
            'id': u.id,
            'full_name': u.full_name(),
            'department': u.get_education_department(),
            'courses': u.get_count_courses(),
            'seminars': u.get_count_seminars(),
            'olympiads': u.get_count_olympiads(),
            'projects': u.get_count_projects(),
        })
    return render(
        request,
        'students.html',
        {
            'students': students,
            'departments': departments
        }
    )


def courses(request):
    courses_ = Course.objects.all()
    for c in courses_:
        c.default_departments_ = c.default_departments.get_queryset()
    return render(request, 'courses.html', {'courses': courses_})


def courses_edit(request, id):
    if request.method == 'GET':
        course = Course.objects.get(pk=id)
        form = CourseEdit(instance=course)
        return render(request, 'courses_edit.html', {'form': form})
    elif request.method == 'POST':
        form = CourseEdit(request.POST)
        return HttpResponse()
    else:
        HttpResponse()

def import_(request):
    if request.method == 'POST':
        try:
            files = request.FILES.getlist('data_files')
            results_ungrouped=[]
            import_func_map = {
                'education': import_education,
                'course': import_course,
                'seminar': import_seminar,
                'project': import_project,
                'olympiad': import_olympiad,
            }
            try:
                with transaction.atomic():
                    for file in files:
                        doc = opendocument.load( file.file )
                        parsed = doc_parse( doc )
                        for k in parsed:
                            for rec in parsed[k]:
                                results_ungrouped += import_func_map[k]( rec )
            except DataFormatException as e:
                return render(request, 'import_finished.html', {'error': e})

            grouped = group_by_type(results_ungrouped)
            results = []
            type_mappings = {
                User: {'cat': 'Пользователи'},
                Department: {'cat': 'Площадки'},
                Education: {'cat': 'Обучения'},
                Subject: {'cat': 'Предметы'},
                Location: {'cat': 'Места'},
                Activity: {'cat': 'Деятельности'},
                Course: {'cat': 'Курсы'},
                Seminar: {'cat': 'Семинары'},
                Project: {'cat': 'Проекты'},
                Olympiad: {'cat': 'Олимпиады'},
                CourseParticipation: {'cat': 'Участия в курсах'},
                SeminarParticipation: {'cat': 'Участия в семинарах'},
                ProjectParticipation: {'cat': 'Участия в проектах'},
                OlympiadParticipation: {'cat': 'Участия в олимпиадах'},
            }
            for t in list(grouped.keys()):
                unique = list( set( map(lambda x: str(x), grouped[t]) ) )
                unique.sort()
                mapping = dict( type_mappings[t] )
                mapping['objects'] = unique
                results.append( mapping )

            return render(request, 'import_finished.html', {'results': results})

        except Exception as e:
            raise e
    else:
        return render(request, 'import.html')


def tasks(request):
    return render(request, 'tasks.html')


def print_(request):

    dep_years_ = {}

    for edu in Education.objects.all():
        add_to_dict_multival_set(
            dep_years_,
            edu.department,
            edu.finish_date.year
        )

    dep_years = {}
    for d in dep_years_:
        s = list(dep_years_[d])
        s.sort()
        dep_years[d] = s

    return render(
        request,
        'print.html',
        {
            'dep_years': dep_years
        }
    )


def print_dep_year(request, dep, year, format_):
    if format_ not in ['pdf', 'odt']:
        return HttpResponseBadRequest()

    student_ids = set(
        map(
            lambda r: r['student__id'],
            Education.objects.filter(
                finish_date__year=year,
                department__id=dep
            ).values('student__id')
        )
    )
    doc = generate_document_for_many_students(student_ids)
    odt = document_to_odt_data(doc)

    if format_ == 'odt':
        data = odt
    else:
        data = odt_data_to_pdf_reader( odt ).stream
        data.seek(0)

    dep_name = Department.objects.get(pk=dep).name
    response = FileResponse(
        data,
        content_type='application/vnd.oasis.opendocument.text' if format_ == 'odt' else 'application/pdf',
        filename=f"Зачетки выпускников {year} года, {dep_name}.{format_}"
    )
    return response


def student_profile(request, id):
    user = User.objects.filter(id=id)
    if not user:
        return render(request, "errors/404.html", {})
    else:
        user = user[0]
    edu = Education.objects.filter(student__id=id)
    cp = CourseParticipation.objects.filter(student__id=id)
    sp = SeminarParticipation.objects.filter(student__id=id)
    pp = ProjectParticipation.objects.filter(student__id=id)
    op = OlympiadParticipation.objects.filter(student__id=id)
    return render(request, 'student_profile.html', {
        'id': id,
        'user': user,
        'educations': edu,
        'course_participations': cp,
        'seminar_participations': sp,
        'project_participations': pp,
        'olympiad_participations': op,
    })


def student_report(request, sid, format_):
    if format_ not in ['pdf', 'odt']:
        return HttpResponseBadRequest()

    report = document_to_odt_data(generate_document_for_student(sid))
    student = User.objects.get(pk=sid)

    if format_ == 'odt':
        data = report
    else:
        data = odt_data_to_pdf_reader( report ).stream
        data.seek(0)

    response = FileResponse(
        data,
        content_type='application/vnd.oasis.opendocument.text' if format_ == 'odt' else 'application/pdf',
        filename=f"Зачетка {student.last_name} {student.first_name} {student.middle_name} {datetime.now().year} год.{format_}"
    )
    return response

