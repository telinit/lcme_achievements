import logging
import os
import tempfile
from ctypes import ArgumentError
from io import FileIO, BytesIO
from typing import Callable

from django.core import serializers
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Model, Count, Sum, Max, Q
from django.forms import Form
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
import zipfile


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

def check_names(request):
    db_ru_names = os.path.join(settings.BASE_DIR, 'main_app/static/russian_names.json')
    db_ru_surnames = os.path.join(settings.BASE_DIR, 'main_app/static/russian_surnames.json')
    db_foreign_names = os.path.join(settings.BASE_DIR, 'main_app/static/foreign_names.json')

    name_gender = {}
    surnames = set()

    added_gender: list[Tuple[int, str, str, str]] = []
    wrong_names: list[Tuple[int, str]] = []
    wrong_surnames: list[Tuple[int, str]] = []

    for ndb in [db_ru_names, db_foreign_names]:
        f = open(ndb, 'r', encoding='utf8')
        js = json.load(f)
        for o in js:
            if 'Sex' in o:
                gender = 'M' if o['Sex'] == 'М' else 'F'  # Those are different 'M' letters (en and ru)
            elif 'gender' in o:
                gender = 'M' if o['gender'] == 'Male' else 'F'
            else:
                continue

            if 'Name' in o:
                name = str(o['Name'])
            elif 'name' in o:
                name = str(o['name'])
            else:
                continue

            name_gender[name.capitalize()] = gender

    for sdb in [db_ru_surnames]:
        f = open(sdb, 'r', encoding='utf8')
        js = json.load(f)

        for o in js:
            if 'Surname' in o:
                surnames.add( str(o['Surname']).capitalize() )
            else:
                continue

    all_names = User.objects\
        .all()\
        .values('id', 'first_name', 'last_name', 'gender')

    for n in all_names:
        (id, first_name, last_name, gender) = (
            n['id'], n['first_name'], n['last_name'], n['gender']
        )
        new_gender = name_gender[first_name] if first_name in name_gender else None
        print(id, first_name, last_name, gender, new_gender)
        if not gender and new_gender:
            added_gender.append((id, first_name, last_name, new_gender))
            u = User.objects\
                .get(id=id)

            u.gender = new_gender
            u.save()

        if first_name not in name_gender.keys():
            wrong_names.append((id, first_name))

        if last_name not in surnames:
            wrong_surnames.append((id, last_name))

    return render(
        request,
        'tasks/check_names.html',
        {
            'added_gender': added_gender,
            'wrong_names': wrong_names,
            'wrong_surnames': wrong_surnames
        }
    )


def print_index(request):
    return render(
        request,
        'print/index.html'
    )


def print_everything(request):
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
    log = logging.getLogger(__name__)
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

    dep_name = Department.objects.get(pk=dep).name

    log.info('Generating the reports for %d students, dep = %s', len(student_ids), dep_name)

    zip_file_name = f'Зачетные книжки выпускников {year} года, {dep_name}.zip'
    log.info('ZIP file name: %s', zip_file_name)

    zip_buff = BytesIO()
    zip = zipfile.ZipFile(zip_buff, 'w', zipfile.ZIP_DEFLATED)

    for i, id in enumerate(student_ids):
        student = User.objects.get(id=id)

        log.info('Generating a report for student with id = %d, name = %s %s %s', id, student.last_name, student.first_name, student.middle_name)

        log.info('Generating the document')
        doc = generate_document_for_student(id)

        log.info('Converting it to ODT')
        odt = document_to_odt_data(doc)

        if format_ == 'odt':
            data = odt
        else:
            log.info('Converting it to PDF')
            data = odt_data_to_pdf_reader(odt).stream
            data.seek(0)

        file_name = f'{i} {student.last_name} {student.first_name} {student.middle_name}.{format_}'

        log.info('Adding the file to the ZIP archive: %s', file_name)
        zip.writestr(file_name, data.read())

    zip.close()

    log.info('Done creating the archive: length = %d', zip_buff.tell())
    zip_buff.seek(0)

    response = FileResponse(
        zip_buff,
        content_type='application/zip',
        filename=zip_file_name,
    )
    return response


def student_profile(request, id):
    user = User.objects.get(id=id)
    if not user:
        return render(request, "errors/404.html", {})
    else:
        user = user

    if user.gender == 'M':
        user.gender_print = 'Мужской'
    elif user.gender == 'F':
        user.gender_print = 'Женский'
    else:
        user.gender_print = 'Не указан'

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
    log = logging.getLogger(__name__)
    if format_ not in ['pdf', 'odt']:
        return HttpResponseBadRequest()

    log.info('Generating the report')
    report = document_to_odt_data(generate_document_for_student(sid))
    student = User.objects.get(pk=sid)

    if format_ == 'odt':
        data = report
    else:
        log.info('Converting the report to PDF')
        data = odt_data_to_pdf_reader(report).stream

    filename = f"Зачетка {student.last_name} {student.first_name} {student.middle_name} {datetime.now().year} год.{format_}"
    content_type = 'application/vnd.oasis.opendocument.text' if format_ == 'odt' else 'application/pdf'

    log.info('Document length: %d bytes, filename = %s, content_type = %s', data.tell(), filename, content_type)

    data.seek(0)

    response = FileResponse(
        data,
        content_type=content_type,
        filename=filename,
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


def edit_merge(request: HttpRequest):
    if not request.POST['object_type'] or not request.POST['object_ids']:
        return HttpResponseBadRequest()
    else:
        Form
        pass


def edit_bulk(request: HttpRequest):
    return None


def stats(request: HttpRequest):
    stats_list = []

    grad_dep = Education.objects\
            .order_by('-finish_date__year', 'department__name') \
            .distinct()\
            .values_list('finish_date__year', 'department__name')

    i = 0
    for year, dep in grad_dep:
        graduated_students = set(
            Education.objects\
            .filter(finish_date__year=year, department__name=dep)\
            .values_list('student__id', flat=True)
        )
        graduated_count = len(graduated_students)
        sum_hours = list(map(
            lambda rec: rec['sum_hours'],
            CourseParticipation.objects
                .filter(student__id__in=graduated_students, is_exam=False)
                .values('student__id')
                .annotate(sum_hours=Sum('hours'))
        ))
        max_sum_hours = max(sum_hours)
        avg_sum_hours = sum(sum_hours) / len(sum_hours)
        count_courses = list(map(
            lambda rec: rec['count_courses'],
            CourseParticipation.objects.filter(student__id__in=graduated_students).values('student__id').annotate(
                count_courses=Count('id'))
        ))
        max_count_courses = max(count_courses)
        avg_count_courses = sum(count_courses) / len(count_courses)

        olymp_part = OlympiadParticipation.objects.filter(student__id__in=graduated_students)
        olymp_count = list(map(
            lambda rec: rec['olymp_count'],
            olymp_part.values('student__id').annotate(
                olymp_count=Count('id'))
        ))
        max_olymp_count = max(olymp_count)

        olymp_awards_q1 = ~Q(title='')
        olymp_awards_q2 = ~Q(prize='')
        olymp_awards = olymp_part\
            .filter(olymp_awards_q1 | olymp_awards_q2)\
            .values('title', 'prize')\
            .annotate(count_prize=Count('prize'))\
            .order_by('-count_prize')

        # olymp_awards = set(
        #     map(
        #         lambda o: f'{o["title"]} {o["prize"]}'.strip(),
        #         olymp_awards
        #     )
        # )

        # olymp_awards = list(filter(lambda s: s != '', olymp_awards))
        # olymp_awards.sort()

        stats_list.append({
            'anchor': f'id{i}',
            'year': year,
            'dep': dep,
            'graduated_count': graduated_count,
            'max_sum_hours': max_sum_hours,
            'avg_sum_hours': avg_sum_hours,
            'max_count_courses': max_count_courses,
            'avg_count_courses': avg_count_courses,
            'max_olymp_count': max_olymp_count,
            'olymp_awards': olymp_awards
        })
        i += 1

    return render(request, 'stats.html', {'stats': stats_list})