from django.core import serializers
from django.db import transaction
from django.db.models import F, Count
from django.http import HttpResponse
from django.shortcuts import render
import csv

# Create your views here.
from django.template import loader

from .forms import CourseEdit, DataImportForm
from .models import User, Education, Course, CourseParticipation, SeminarParticipation, ProjectParticipation, \
    OlympiadParticipation, Project, Olympiad, Seminar
from .util.data_import import *


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
    return render(request, 'students.html', {'students': students})


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
            form = DataImportForm(request.POST)
            if form.is_valid():
                print(form.cleaned_data)
                csv_data: str = form.cleaned_data['data_content']
                csv_rows = csv.DictReader(csv_data.splitlines(), delimiter='\t')
                results = []

                try:
                    with transaction.atomic():
                        if form.cleaned_data['data_type'] == 0:
                            for edu in csv_rows:
                                results += import_education(edu)
                        elif form.cleaned_data['data_type'] == 1:
                            for course in csv_rows:
                                results += import_course(course)
                        elif form.cleaned_data['data_type'] == 2:
                            for sem in csv_rows:
                                results += import_seminar(sem)
                        elif form.cleaned_data['data_type'] == 3:
                            for proj in csv_rows:
                                results += import_project(proj)
                        elif form.cleaned_data['data_type'] == 4:
                            for ol in csv_rows:
                                results += import_olympiad(ol)
                        else:
                            pass  # TODO
                except DataFormatException as e:
                    return render(request, 'import_finished.html', {'error': e})

                return render(request, 'import_finished.html', {'results': results})
            else:
                pass
        except Exception as e:
            raise e
    else:
        return render(request, 'import.html')


def tasks(request):
    return render(request, 'tasks.html')


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


def student_report(request, sid):
    from .reports.student_report import generate_for_student
    report = generate_for_student(sid)
    print(report)

    return HttpResponse(report, content_type='application/vnd.oasis.opendocument.text')

