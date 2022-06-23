from ctypes import ArgumentError
from typing import Callable

from django.core import serializers
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Model
from django.http import HttpResponse, FileResponse, HttpResponseBadRequest, HttpRequest, HttpResponseForbidden, \
    HttpResponseServerError
from django.shortcuts import render
from django.utils.html import escape
from fuzzywuzzy import fuzz

from .forms import CourseEdit
from .reports.student_report import generate_document_for_many_students, document_to_odt_data, \
    generate_document_for_student, odt_data_to_pdf_reader
from .util.data_import import *
from .util.util import group_by_type, add_to_dict_multival_set


# Create your views here.


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
    users = User.objects.filter(education__isnull=False).distinct().order_by('id')
    departments = Department.objects.all().order_by('id')
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


def import_combined_data(data, strict=True):
    results = []

    import_func_map = {
        'education': import_education,
        'course': import_course,
        'seminar': import_seminar,
        'project': import_project,
        'olympiad': import_olympiad,
    }

    for k in data:
        for rec in data[k]:
            try:
                func = import_func_map[k]
                res = func(rec, strict=strict)
                if res:
                    results += res
            except Exception as e:
                if strict:
                    raise e
                else:
                    pass

    return results


def import_(request: HttpRequest):
    if request.method == 'POST':
        try:
            files: Iterable[UploadedFile] = request.FILES.getlist('data_files')
            use_old_format = request.POST.get('use_old_format')
            results_ungrouped = []

            try:
                with transaction.atomic():
                    combined_data = {}
                    parsed_data = {}

                    for file in files:
                        doc = opendocument.load(file.file)
                        if use_old_format:
                            parsed_data = doc_parse_old_and_ugly_format(
                                doc,
                                filename=file.name
                            )
                        else:
                            parsed_data = doc_parse(doc)

                        for k in parsed_data:
                            if k in combined_data:
                                combined_data[k] += parsed_data[k]
                            else:
                                combined_data[k] = parsed_data[k]

                    combined_data['education'] = stitch_educations(combined_data['education'])
                    combined_data = sanitize_dict_vals(combined_data)
                    results_ungrouped = import_combined_data(combined_data, strict=False)
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
                unique = list(set(map(lambda x: str(x), grouped[t])))
                unique.sort()
                mapping = dict(type_mappings[t])
                mapping['objects'] = unique
                results.append(mapping)

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
        data = odt_data_to_pdf_reader(odt).stream
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
    cp = CourseParticipation.objects.filter(student__id=id, is_exam=False)
    ex = CourseParticipation.objects.filter(student__id=id, is_exam=True)
    sp = SeminarParticipation.objects.filter(student__id=id)
    pp = ProjectParticipation.objects.filter(student__id=id)
    op = OlympiadParticipation.objects.filter(student__id=id)
    return render(request, 'student_profile.html', {
        'id': id,
        'user': user,
        'educations': edu,
        'course_participations': cp,
        'exam_participations': ex,
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
        data = odt_data_to_pdf_reader(report).stream
        data.seek(0)

    response = FileResponse(
        data,
        content_type='application/vnd.oasis.opendocument.text' if format_ == 'odt' else 'application/pdf',
        filename=f"Зачетка {student.last_name} {student.first_name} {student.middle_name} {datetime.now().year} год.{format_}",
        as_attachment=True
    )
    return response


def dedupe_edu(request):
    def to_seconds(date):
        import time
        return time.mktime(date.timetuple())

    try:
        edus = Education.objects.all()
        edus_group_by_student = {}
        for e in edus:
            add_to_dict_multival(edus_group_by_student, e.student.id, e)

        cnt_dupes = 0

        for sid in edus_group_by_student:
            stud_edus: list[Education] = list(edus_group_by_student[sid])
            if not stud_edus:
                continue

            stud_edus.sort(
                key=lambda e: to_seconds(e.start_date)
            )

            head = stud_edus.pop(0)

            for edu in stud_edus:
                if head.department == edu.department:
                    head.start_date = min(head.start_date, edu.start_date)
                    head.finish_date = max(head.finish_date, edu.finish_date)
                    head.save()
                    edu.delete()
                    cnt_dupes += 1
                else:
                    head = edu

        return HttpResponse(f"Дедупликация успешно завершена. Удалено дублей: {cnt_dupes}".encode())
    except Exception as e:
        return HttpResponseServerError(
            f"Error occured: {type(e).__name__}: {e}".encode()
        )


def bulk_edit():
    pass


def find_similar_objects(request, obj_type: str, method: str, limit: int):
    obj_type_class_map: dict[str, type] = {
        'user': User,
        'location': Location,
        'department': Department,
        'education': Education,
        'subject': Subject,
        'activity': Activity,
        'course': Course,
        'seminar': Seminar,
        'project': Project,
        'olympiad': Olympiad,
        'award': Award,
        'participation': Participation,
        'courseparticipation': CourseParticipation,
        'seminarparticipation': SeminarParticipation,
        'projectparticipation': ProjectParticipation,
        'olympiadparticipation': OlympiadParticipation
    }
    obj_type_str_map: dict[str, Callable[[Model], str]] = {
        'user': User.full_name,
        'location': Location.__str__,
        'department': Department.__str__,
        'education': Education.__str__,
        'subject': Subject.__str__,
        'activity': Activity.__str__,
        'course': Course.__str__,
        'seminar': Seminar.__str__,
        'project': Project.__str__,
        'olympiad': Olympiad.__str__,
        'award': Award.__str__,
        'participation': Participation.__str__,
        'courseparticipation': CourseParticipation.__str__,
        'seminarparticipation': SeminarParticipation.__str__,
        'projectparticipation': ProjectParticipation.__str__,
        'olympiadparticipation': OlympiadParticipation.__str__
    }

    if obj_type not in obj_type_str_map or obj_type not in obj_type_class_map:
        return HttpResponseBadRequest(b'Bad object type')

    obj_class = obj_type_class_map[obj_type]
    objects: list[User] = list(obj_class.objects.all())

    f_str = obj_type_str_map[obj_type]
    results = find_nearest_objects(limit, objects, str_func=f_str)

    results_objs = map(
        lambda t: {
            'ratio': t[0],
            'object1_name': f_str(t[1]),
            'object2_name': f_str(t[2]),
            'object1_id': t[1].id,
            'object2_id': t[2].id
        },
        results
    )

    return render(request, 'similar_objects.html', {'results': results_objs})


def find_nearest_objects(
        limit: int,
        objects: list[models.Model],
        str_func: Callable[[models.Model], str] = str,
        method: str = 'ratio'
) -> list[Tuple[int, models.Model, models.Model]]:
    l = len(objects)
    result: list[Tuple[int, models.Model, models.Model]] = []  # (ratio, object1, object2)

    cmp_func_map: dict[str, Callable[[str, str], int]] = {
        'ratio':                    fuzz.ratio,
        'partial_ratio':            fuzz.partial_ratio,
        'UQRatio':                  fuzz.UQRatio,
        'QRatio':                   fuzz.QRatio,
        'partial_token_set_ratio':  fuzz.partial_token_set_ratio,
        'partial_token_sort_ratio': fuzz.partial_token_sort_ratio,
        'token_set_ratio':          fuzz.token_set_ratio,
        'token_sort_ratio':         fuzz.token_sort_ratio,
        'UWRatio':                  fuzz.UWRatio,
        'WRatio':                   fuzz.WRatio,
    }

    if method not in cmp_func_map:
        raise ArgumentError('Bad method')

    cmp_func = cmp_func_map[method]

    for obj_ix1 in range(l):
        for obj_ix2 in range(obj_ix1 + 1, l):
            ratio = cmp_func(
                str_func(objects[obj_ix1]),
                str_func(objects[obj_ix2])
            )
            x = (ratio, objects[obj_ix1], objects[obj_ix2])

            if len(result) == 0:
                result.append(x)
                continue
            if len(result) > limit and result[-1][0] >= ratio:
                continue
            for i, (ratio_, object1, object2) in enumerate(result):
                if ratio > ratio_:
                    result.insert(i, x)
                    if len(result) > limit:
                        result.pop()
                    break
    return result
