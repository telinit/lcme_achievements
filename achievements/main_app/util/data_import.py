from ..models import *


class DataFormatException(Exception):
    pass


def cap_first(s):
    return s[0].upper() + s[1:] if s != '' else ''


def transliterate(s: str) -> str:
    eng = ['a', 'b', 'v', 'g', 'd', 'e', 'j', 'z', 'i',
           'j', 'k', 'l', 'm', 'n', 'o', 'p', 'r', 's', 't',
           'u', 'f', 'h', 'c', 'ch', 'sh', 'sh', '\'', 'i', '\'', 'e', 'yu', 'ya', '_', 'yo']

    def tr(c1: str):
        i = ord(c1.lower()) - ord('а')
        c2 = eng[i] if len(eng) > i >= 0 else c1

        if c1 == c1.upper():
            return c2.capitalize()
        else:
            return c2

    return "".join(map(tr, s))


def make_username(first_name: str, middle_name: str, last_name: str) -> str:
    return f'{transliterate(first_name)}_{transliterate(middle_name)}_{transliterate(last_name)}'


def generate_password(length: int = 10) -> str:
    import random

    alph = '123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    pw = ''
    for i in range(length):
        i = random.randint(0, len(alph) - 1)
        pw += alph[i]

    return pw


def user_get_or_create(data, ln='Фамилия', fn='Имя', mn='Отчество'):
    user = User.objects.filter(
        last_name=cap_first( data[ln].strip()),
        first_name=cap_first( data[fn].strip()),
        middle_name=cap_first( data[mn].strip())
    )
    if not user:
        username = make_username(
            cap_first( data[fn].strip()),
            cap_first( data[mn].strip()),
            cap_first( data[ln].strip())
        )
        user = User(username=username)
        user.set_password(generate_password())
        user.password_clear = generate_password()
    else:
        user = user[0]

    if 'Контактный телефон' in data:
        user.phone_number = cap_first( data['Контактный телефон'].strip())

    if 'Контактный email' in data:
        user.email = cap_first( data['Контактный email'].strip())

    user.first_name = cap_first( data[fn].strip())
    user.middle_name = cap_first( data[mn].strip())
    user.last_name = cap_first( data[ln].strip())

    user.save()

    return user


def department_get_or_create(name):
    dep = Department.objects.filter(name=name)
    if not dep:
        dep = Department(name=name)
        dep.save()
    else:
        dep = dep[0]

    return dep


def subject_get_or_create(name):
    sub = Subject.objects.filter(name=name)
    if not sub:
        sub = Subject(name=name)
        sub.save()
    else:
        sub = sub[0]

    return sub


def location_get_or_create(name):
    loc = Location.objects.filter(name=name)
    if not loc:
        loc = Location(name=name)
        loc.save()
    else:
        loc = loc[0]

    return loc


def import_education(data):
    student = user_get_or_create(data)

    dep = department_get_or_create(cap_first(data['Площадка'].strip()))

    edu = Education.objects.filter(
        student__id=student.id,
        department__id=dep.id,
        start_year=cap_first( data['Год поступления'].strip()),
        start_class=cap_first( data['Класс поступления'].strip()),
        finish_year=cap_first( data['Год завершения'].strip()),
        finish_class=cap_first( data['Класс завершения'].strip())
    )
    if not edu:
        edu = Education(
            student=student,
            department=dep,
            start_year=cap_first( data['Год поступления'].strip()),
            start_class=cap_first( data['Класс поступления'].strip()),
            finish_year=cap_first( data['Год завершения'].strip()),
            finish_class=cap_first( data['Класс завершения'].strip())
        )
        edu.save()
    else:
        edu = edu[0]

    return [student, dep, edu]


def import_course(data):
    from datetime import datetime

    # Fields
    # "Фамилия", "Имя", "Отчество", "Название", "Глава", "Предмет", "Количество часов",
    # "Начало", "Завершение", "Место проведения", "Оценка/зачёт",
    # "Фамилия преподавателя", "Имя преподавателя", "Отчество преподавателя"

    for key in data:
        if data[key].strip() == '' and key != 'Оценка/зачёт' and key != 'Глава':
            raise DataFormatException(f'Пустое поле: {key}, строка: {data}')

    location_raw = cap_first( data["Место проведения"].strip())
    subject_raw = cap_first( data["Предмет"].strip())

    student = user_get_or_create(data)
    teacher = user_get_or_create(data, "Фамилия преподавателя", "Имя преподавателя", "Отчество преподавателя")
    subject = subject_get_or_create(subject_raw)
    location = location_get_or_create(location_raw)

    course = Course.objects.filter(
        name=cap_first( data["Название"].strip()),
        location=location,
        chapter=cap_first( data["Глава"].strip()),
        subject=subject
    )

    if not course:
        course = Course(
            name=cap_first( data["Название"].strip()),
            location=location,
            chapter=cap_first( data["Глава"].strip()),
            subject=subject
        )
        course.save()
    else:
        course = course[0]

    cp = CourseParticipation.objects.filter(
        student=student,
        started=datetime.strptime(data["Начало"].strip(), "%d.%m.%Y"),
        finished=datetime.strptime(data["Завершение"].strip(), "%d.%m.%Y"),
        course=course,
        hours=int(data["Количество часов"].strip()),
        teacher=teacher,
        mark=data["Оценка/зачёт"].strip()
    )

    if not cp:
        cp = CourseParticipation(
            student=student,
            started=datetime.strptime(data["Начало"].strip(), "%d.%m.%Y"),
            finished=datetime.strptime(data["Завершение"].strip(), "%d.%m.%Y"),
            course=course,
            hours=int(data["Количество часов"].strip()),
            teacher=teacher,
            mark=data["Оценка/зачёт"].strip()
        )
        cp.save()
    else:
        cp = cp[0]

    return [student, teacher, subject, location, course, cp]


def import_seminar(data):
    pass


def import_project(data):
    pass


def import_olympiad(data):
    pass
