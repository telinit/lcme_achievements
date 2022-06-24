import os
import pathlib
import sys
import traceback
from datetime import datetime
from traceback import print_exc
from typing import Iterable, Tuple, Any

from odf import opendocument
from odf.element import Element
from odf.opendocument import OpenDocumentText, OpenDocumentSpreadsheet
from odf.table import Table, TableRow, TableCell

from ..models import *
from .util import add_to_dict_multival


class DataFormatException(Exception):
    pass


def cap_first(s):
    return s[0].upper() + s[1:] if s != '' else ''


def transliterate(s: str) -> str:
    eng = ['a', 'b', 'v', 'g', 'd', 'e', 'j', 'z', 'i',
           'j', 'k', 'l', 'm', 'n', 'o', 'p', 'r', 's', 't',
           'u', 'f', 'h', 'c', 'ch', 'sh', 'sh', '\'', 'i',
           '\'', 'e', 'yu', 'ya', '_', 'yo']

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


def get_sheet_by_idx( doc, sheetIndex ):
    try:
        spreadsheet = doc.spreadsheet
    except NameError:
        sys.stderr.write("Error: file is not a spreadsheet\n")
        return

    sheets = spreadsheet.getElementsByType( Table )
    if sheetIndex > len( sheets ):
        sys.stderr.write( "Error: spreadsheet has only %d sheets; requested invalid sheet %d\n" % (len( sheets ), sheetIndex + 1) )
        return

    sheet = sheets[sheetIndex]
    return sheet


def get_element_attribute(elem: Element, key: str) -> str:
    for k in elem.attributes:
        (ns, attr) = k
        if attr == key:
            return elem.attributes[k]


def get_sheet_name(sheet: Element) -> str:
    return get_element_attribute(sheet, 'name')


def doc_get_sheets(doc: OpenDocumentSpreadsheet) -> Iterable[Table]:
    return doc.spreadsheet.getElementsByType( Table )


def doc_get_sheet_names(doc: OpenDocumentSpreadsheet) -> Iterable[str]:
    for s in doc_get_sheets(doc):
        yield get_sheet_name(s)


def get_sheet_by_name( doc: OpenDocumentSpreadsheet, sheet_name: str ):
    try:
        spreadsheet = doc.spreadsheet
    except NameError:
        sys.stderr.write("Error: file is not a spreadsheet\n")
        return

    sheets = doc_get_sheets(doc)

    for s in sheets:
        if get_sheet_name(s) == sheet_name:
            return s


record = dict[str, str]
csv_data = list[record]
list2d = list[list[str]]


def ints(start=0) -> Iterable[int]:
    i = start
    while True:
        yield i
        i += 1


def it_ix(it: Iterable[Any]) -> Iterable[Tuple[int, Any]]:
    return zip( ints(), it )


def row_to_strings(row: TableRow, empty_cell_stop_threshhold=10) -> list[str]:
    res = []
    empty_cnt = 0
    for cell in row.getElementsByType(TableCell):
        mul = get_element_attribute(cell, 'number-columns-repeated')
        mul = int(mul) if mul else 1

        txt = str(cell)
        if txt == '':
            if empty_cnt + mul >= empty_cell_stop_threshhold:
                return res[0:-empty_cnt] if empty_cnt > 0 else res

            empty_cnt += mul
        else:
            empty_cnt = 0


        for i in range(mul):
            res.append(txt)

    return res


def sheet_to_list2d(sheet: Table) -> list2d:
    res = []
    for row in sheet.getElementsByType(TableRow):
        strs = row_to_strings(row)
        if len(strs) <= 0:
            continue
        res.append(strs)

    return res


def list2d_crop_before_point(data: list2d, row_num: int, col_num: int) -> list2d:
    res = []
    for (i, row) in zip( range(len(data)), data):
        if i < row_num:
            continue
        new_row = []
        for (j, cell) in zip( range(len(row)), row):
            if j < col_num:
                continue
            new_row.append(cell)
        res.append(new_row)
    return res


def crop_list2d_csv_like(data: list2d) -> list2d:
    if data == [] or data[0] == []:
        return data

    empty_idx = -1
    for (i,c) in zip( range(len(data[0])), data[0] ):
        if c.strip() == '':
            empty_idx = i

    if empty_idx < 0:
        return data

    result = []
    for row in data:
        result.append(row[0:empty_idx])

    return result


def list2d_to_csv_data(data: list2d, strip_str=False, lower_header=False, dedupe_key=False) -> csv_data:
    if data == [] or data[0] == []:
        return []

    result = []
    header = data[0]
    for row in data[1:]:
        rec = {}
        for (i, r, h) in zip( ints(), row, header ):
            a = h.strip() if strip_str else h
            b = r.strip() if strip_str else r

            a = a.lower() if lower_header else a

            if dedupe_key and a in rec:
                rec[f'{a}-{i}'] = b
            else:
                rec[a] = b
        result.append(rec)

    return result


def str_has_words(text: str, words: str) -> bool:
    text_words = list(map(lambda s: s.lower(), text.split()))
    words_words = list(map(lambda s: s.lower(), words.split()))
    for w in words_words:
        if w not in text_words:
            return False
    return True


def sheet_to_csv(sheet: Table, stop_at_empty_row=True) -> csv_data:
    result: list[dict[str, str]] = []
    header: list[str] = []
    rows = sheet.getElementsByType(TableRow)

    for row in rows:
        vals: list[str] = []
        cells = row.getElementsByType(TableCell)
        for cell in cells:
            rep = get_element_attribute(cell, 'number-columns-repeated')
            if rep:
                rep_n = int(rep)
            else:
                rep_n = 1
            s = str(cell)
            if not header and not s:
                break
            for i in range(rep_n):
                if header and len(vals) >= len(header):
                    break
                else:
                    vals.append(s)
        if not header:
            header = vals
        else:
            if stop_at_empty_row:
                if all( map(lambda x: x == '', vals) ):
                    break
            rec: dict[str, str] = {}
            if len(vals) < len(header):
                vals += [''] * (len(header) - len(vals))
            assert len(header) == len(vals)
            for i in range(len(header)):
                rec[header[i]] = vals[i].strip()
            result.append(rec)

    return result


def doc_to_csv_data(doc: OpenDocumentSpreadsheet, sheet_name: str) -> csv_data:
    return sheet_to_csv( get_sheet_by_name( doc, sheet_name ) )


def doc_parse(doc: OpenDocumentSpreadsheet) -> dict[str, csv_data]:
    return {
        'education': doc_to_csv_data(doc, '0. Общая информация'),
        'course': doc_to_csv_data(doc, '1. Образование'),
        'seminar': doc_to_csv_data(doc, '2. Семинары'),
        'project': doc_to_csv_data(doc, '3. Проект-исследование'),
        'olympiad': doc_to_csv_data(doc, '4. Конкурсы и олимпиады'),
    }


def user_get_or_create(data, ln='Фамилия', fn='Имя', mn='Отчество'):
    if data['Фамилия'] == 'Райцин':
        iii = 0
        pass

    username = make_username(
        cap_first(data[fn].strip()),
        cap_first(data[mn].strip()),
        cap_first(data[ln].strip())
    )

    user, created = User.objects.get_or_create (
        # last_name=cap_first( cap_first( data[ln].strip() )),
        # first_name=cap_first( cap_first( data[fn].strip() )),
        # middle_name=cap_first( cap_first( data[mn].strip() ))
        username = username
    )
    if created:
        # old_user = User.objects.filter(username = username)
        user.username = username
        user.set_password(generate_password())
        user.password_clear = generate_password()

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


def sanitize_list_vals(l: list, recurse=True) -> list:
    if not l:
        return []
    else:
        res = []
        for x in l:
            if type(x) is list and recurse:
                res.append( sanitize_list_vals(x, recurse) )
            elif type(x) is dict and recurse:
                res.append(sanitize_dict_vals(x, recurse) )
            elif x is None:
                res.append('')
            else:
                res.append(x)
        return res


def sanitize_dict_vals(d: dict, recurse=True) -> dict:
    if not d:
        return dict()
    else:
        res = dict()
        for k in d:
            if d[k] is None:
                res[k] = ""
            else:
                if type(d[k]) is dict and recurse:
                    res[k] = sanitize_dict_vals(d[k], recurse)
                elif type(d[k]) is list and recurse:
                    res[k] = sanitize_list_vals(d[k], recurse)
                else:
                    res[k] = d[k]
        return res


def import_education(data, strict=True) -> list[Any]:
    try:
        student = user_get_or_create(data)

        dep = department_get_or_create(cap_first(data['Площадка'].strip()))

        edu = Education.objects.filter(
            student__id=student.id,
            department__id=dep.id,
            start_date=datetime.strptime(data['Дата поступления'].strip(), "%d.%m.%Y"),
            start_class=cap_first( data['Класс поступления'].strip()),
            finish_date=datetime.strptime(data['Дата завершения'].strip(), "%d.%m.%Y"),
            finish_class=cap_first( data['Класс завершения'].strip())
        )
        if not edu:
            edu = Education(
                student=student,
                department=dep,
                start_date=datetime.strptime(data['Дата поступления'].strip(), "%d.%m.%Y"),
                start_class=cap_first( data['Класс поступления'].strip()),
                finish_date=datetime.strptime(data['Дата завершения'].strip(), "%d.%m.%Y"),
                finish_class=cap_first( data['Класс завершения'].strip())
            )
            edu.save()
        else:
            edu = edu[0]

        return [student, dep, edu]
    except Exception as e:
        if strict:
            raise e
        else:
            return []


def import_course(data, strict=True) -> list[Any]:
    try:
        from datetime import datetime

        # Fields
        # "Фамилия", "Имя", "Отчество", "Название", "Глава", "Предмет", "Количество часов",
        # "Начало", "Завершение", "Место проведения", "Оценка/зачёт",
        # "Фамилия преподавателя", "Имя преподавателя", "Отчество преподавателя"

        for key in data:
            if data[key].strip() == '' and key != 'Оценка/зачёт' and key != 'Глава':
                if strict:
                    raise DataFormatException(f'Пустое поле: {key}, строка: {data}')
                else:
                    return []

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
            mark=data["Оценка/зачёт"].strip(),
            is_exam=data["Экзамен"].strip().lower() == 'да'
        )

        if not cp:
            cp = CourseParticipation(
                student=student,
                started=datetime.strptime(data["Начало"].strip(), "%d.%m.%Y"),
                finished=datetime.strptime(data["Завершение"].strip(), "%d.%m.%Y"),
                course=course,
                hours=int(data["Количество часов"].strip()),
                teacher=teacher,
                mark=data["Оценка/зачёт"].strip(),
                is_exam=data["Экзамен"].strip().lower() == 'да'
            )
            cp.save()
        else:
            cp = cp[0]

        return [student, teacher, subject, location, course, cp]
    except Exception as e:
        if strict:
            raise DataFormatException(f'Ошибка импорта: {type(e).__name__}: {e}')
        else:
            return []


def import_seminar(data, strict=True) -> list[Any]:
    from datetime import datetime

    # Fields
    # "Фамилия", "Имя", "Отчество",
    # "Название семинара", "Предмет", "Количество часов",
    # "Оценка/зачёт", "Начало", "Завершение", "Место проведения",
    # "Фамилия преподавателя", "Имя преподавателя", "Отчество преподавателя"

    for key in data:
        if data[key].strip() == '' and key != 'Оценка/зачёт':
            if strict:
                raise DataFormatException(f'Пустое поле: {key}, строка: {data}')
            else:
                return []

    location_raw = cap_first(data["Место проведения"].strip())
    subject_raw = cap_first(data["Предмет"].strip())

    student = user_get_or_create(data)
    teacher = user_get_or_create(data, "Фамилия преподавателя", "Имя преподавателя", "Отчество преподавателя")
    subject = subject_get_or_create(subject_raw)
    location = location_get_or_create(location_raw)

    seminar = Seminar.objects.filter(
        name=cap_first(data["Название семинара"].strip()),
        location=location,
        subject=subject
    )

    if not seminar:
        seminar = Seminar(
            name=cap_first(data["Название семинара"].strip()),
            location=location,
            subject=subject
        )
        seminar.save()
    else:
        seminar = seminar[0]

    sp = SeminarParticipation.objects.filter(
        student=student,
        started=datetime.strptime(data["Начало"].strip(), "%d.%m.%Y"),
        finished=datetime.strptime(data["Завершение"].strip(), "%d.%m.%Y"),
        seminar=seminar,
        hours=int(data["Количество часов"].strip()),
        teacher=teacher,
        mark=data["Оценка/зачёт"].strip()
    )

    if not sp:
        sp = SeminarParticipation(
            student=student,
            started=datetime.strptime(data["Начало"].strip(), "%d.%m.%Y"),
            finished=datetime.strptime(data["Завершение"].strip(), "%d.%m.%Y"),
            seminar=seminar,
            hours=int(data["Количество часов"].strip()),
            teacher=teacher,
            mark=data["Оценка/зачёт"].strip()
        )
        sp.save()
    else:
        sp = sp[0]

    return [student, teacher, subject, location, seminar, sp]


def import_project(data, strict=True) -> list[Any]:
    from datetime import datetime

    # Fields
    # "Фамилия", "Имя", "Отчество",
    # "Название проекта", "Место проведения", "Предмет",
    # "Начало", "Завершение",
    # "Фамилия руководителя", "Имя руководителя", "Отчество руководителя"

    for key in data:
        if data[key].strip() == '':
            if strict:
                raise DataFormatException(f'Пустое поле: {key}, строка: {data}')
            else:
                return []

    location_raw = cap_first(data["Место проведения"].strip())
    subject_raw = cap_first(data["Предмет"].strip())

    student = user_get_or_create(data)
    curator = user_get_or_create(data, "Фамилия руководителя", "Имя руководителя", "Отчество руководителя")
    subject = subject_get_or_create(subject_raw)
    location = location_get_or_create(location_raw)

    project = Project.objects.filter(
        name=cap_first(data["Название проекта"].strip()),
        location=location,
        subject=subject
    )

    if not project:
        project = Project(
            name=cap_first(data["Название проекта"].strip()),
            location=location,
            subject=subject
        )
        project.save()
    else:
        project = project[0]

    pp = ProjectParticipation.objects.filter(
        student=student,
        started=datetime.strptime(data["Начало"].strip(), "%d.%m.%Y"),
        finished=datetime.strptime(data["Завершение"].strip(), "%d.%m.%Y"),
        project=project,
        curator=curator,
    )

    if not pp:
        pp = ProjectParticipation(
            student=student,
            started=datetime.strptime(data["Начало"].strip(), "%d.%m.%Y"),
            finished=datetime.strptime(data["Завершение"].strip(), "%d.%m.%Y"),
            project=project,
            curator=curator,
        )
        pp.save()
    else:
        pp = pp[0]

    return [student, curator, subject, location, project, pp]


def import_olympiad(data, strict=True):
    from datetime import datetime

    # Fields
    # "Фамилия", "Имя", "Отчество",
    # "Этап", "Название конкурса / олимпиады",
    # "Начало", "Завершение", "Место проведения",
    # "Звание", "Награда", "В составе команды"

    for key in data:
        if data[key].strip() == '' and key not in ['Этап', 'Звание', 'Награда', 'В составе команды']:
            if strict:
                raise DataFormatException(f'Пустое поле: {key}, строка: {data}')
            else:
                return []

    location_raw = cap_first(data["Место проведения"].strip())

    student = user_get_or_create(data)
    location = location_get_or_create(location_raw)

    olympiad = Olympiad.objects.filter(
        name=cap_first(data["Название конкурса / олимпиады"].strip()),
        location=location,
        stage=cap_first(data["Этап"].strip()),
    )

    if not olympiad:
        olympiad = Olympiad(
            name=cap_first(data["Название конкурса / олимпиады"].strip()),
            location=location,
            stage=cap_first(data["Этап"].strip()),
        )
        olympiad.save()
    else:
        olympiad = olympiad[0]

    op = OlympiadParticipation.objects.filter(
        olympiad=olympiad,
        student=student,
        started=datetime.strptime(data["Начало"].strip(), "%d.%m.%Y"),
        finished=datetime.strptime(data["Завершение"].strip(), "%d.%m.%Y"),
        title=cap_first(data["Звание"].strip()),
        prize=cap_first(data["Награда"].strip()),
        is_team_member=data["В составе команды"].strip().upper() == 'ДА'
    )

    if not op:
        op = OlympiadParticipation(
            olympiad=olympiad,
            student=student,
            started=datetime.strptime(data["Начало"].strip(), "%d.%m.%Y"),
            finished=datetime.strptime(data["Завершение"].strip(), "%d.%m.%Y"),
            title=cap_first(data["Звание"].strip()),
            prize=cap_first(data["Награда"].strip()),
            is_team_member=data["В составе команды"].strip().upper() == 'ДА'
        )
        op.save()
    else:
        op = op[0]

    return [student, location, olympiad, op]


def doc_parse_old_and_ugly_format(doc: OpenDocumentSpreadsheet, filename: str = "") -> dict[str, csv_data]:
    result = {
        'education': [],
        'course': [],
        'seminar': [],
        'project': [],
        'olympiad': [],
    }

    if filename:
        print(f"Started parsing or file {filename}")

    # Trying to guess sheet names
    sheets = doc_get_sheets(doc)
    sheet_map = {}

    for sheet in sheets:
        n = get_sheet_name(sheet)
        l = n.lower()
        if l == 'ДО (допобразование)'.lower() or l.find('допобразование') >= 0 or n.find('ДО') >= 0:
            sheet_map['do'] = sheet
        elif l == 'Экзамены (сессия)'.lower() or l.find('экзамены') >= 0 or l.find('сессия') >= 0:
            sheet_map['exams'] = sheet
        elif l == 'Семинары'.lower() or l.find('семинары') >= 0:
            sheet_map['seminars'] = sheet
        elif l == 'Проект-исследование'.lower() or l.find('проект') >= 0 or l.find('исследование') >= 0:
            sheet_map['projects'] = sheet
        elif l == 'Участие в конкурсах и олимп. '.lower() or l.find('участие в конкурсах') >= 0 or l.find('олимп') >= 0:
            sheet_map['olympiads'] = sheet
        elif l == 'Летняя школа '.lower() or l.find('летняя') >= 0:
            sheet_map['summer'] = sheet
        else:
            pass

    print(f'By now, we have these mappings ({len(sheet_map)} in total):')
    for k in sheet_map:
        print(f'\t{k} -> \'{get_sheet_name(sheet_map[k])}\'')

    if len(sheet_map) != 6:
        print('WARN: Wrong number of sheets found.')

    h = UglyHelper(filename)

    print("Guessed info from the file name:")
    print(h)

    # ed = input("Modify the data (Y/N)? ")

    ed =    h.graduation_class is None \
         or h.admission_class is None \
         or h.admission_date is None \
         or h.graduation_date is None \
         or h.courses_stared is None \
         or h.courses_finished is None \
         or h.department is None

    if False: # ed: # ed.lower().strip() == 'y':
        deps = [
            'Математическая площадка',
            'Инженерная площадка',
            'Биологическая площадка',
            'Академическая площадка',
            'Гуманитарная площадка',
            'Неизвестная площадка',
        ]
        print('Known departments:')
        for i in range(len(deps)):
            print(f'\t{i}. {deps[i]}')
        h.department = deps[int(input('Choose the department: '))]

        adm_year = input('Enter the admission YEAR of the students: ')
        h.admission_date = '01.09.' + adm_year

        h.admission_class = input('Enter the admission class of the students: ')
        h.graduation_date = '30.05.' + str(int(adm_year) + 12 - int(h.admission_class)) # input('Enter the graduation YEAR of the students: ')
        h.graduation_class = '11' # input('Enter the graduation class of the students: ')
        cs_year = input('Enter the YEAR when the courses started: ')
        h.courses_stared = '01.09.' + cs_year
        h.courses_finished = '30.05.' + str(int(cs_year)+1)# input('Enter the YEAR when the courses finished: ')

    print('OK, continuing...')

    try:
        result['course'] = parse_ugly_do(sheet_map['do'], h)
    except Exception as e:
        print(f"Failed to parse 'do' from {filename}")
        pass
    try:
        result['course'] += parse_ugly_exams(sheet_map['exams'], h)
    except Exception as e:
        print(f"Failed to parse 'exams' from {filename}")
        pass
    try:
        result['course'] += parse_ugly_summer(sheet_map['summer'], h)
    except Exception as e:
        print(f"Failed to parse 'summer' from {filename}")
        pass
    try:
        result['seminar'] = parse_ugly_seminars(sheet_map['seminars'], h)
    except Exception as e:
        print(f"Failed to parse 'seminar' from {filename}")
        pass
    try:
        result['project'] = parse_ugly_projects(sheet_map['projects'], h)
    except Exception as e:
        print(f"Failed to parse 'project' from {filename}")
        pass
    try:
        result['olympiad'] = parse_ugly_olympiads(sheet_map['olympiads'], h)
    except Exception as e:
        print(f"Failed to parse 'olympiad' from {filename}")
        pass
    try:
        result['education'] = generate_ugly_educations(result, h)
    except Exception as e:
        print(f"Failed to parse 'education' from {filename}")
        pass

    return result


class UglyHelper:
    graduation_date = None
    graduation_class = None

    admission_date = None
    admission_class = None

    courses_stared = None
    courses_finished = None

    department = None

    def __init__(self, filename):
        if filename.lower().find('матем') >= 0:
            self.department = 'Математическая площадка'
            self.admission_class = '7'
        if filename.lower().find('академ') >= 0:
            self.department = 'Академическая площадка'
            self.admission_class = '5'
        if filename.lower().find('инж') >= 0:
            self.department = 'Инженерная площадка'
            self.admission_class = '7'
        if filename.lower().find('био') >= 0:
            self.department = 'Биологическая площадка'
            self.admission_class = '7'
        if filename.lower().find('гум') >= 0:
            self.department = 'Гуманитарная площадка'
            self.admission_class = '8'

        if self.department == 'Академическая площадка':
            self.graduation_class = '6'
        else:
            self.graduation_class = '11'

        courses_stared_year = None
        courses_finished_year = None
        current_class = None
        admission_year = None

        import re
        m = re.search(r'(\d{4}).(\d{4})', filename)
        if m:
            self.courses_stared = '01.09.' + m.group(1)
            self.courses_finished = '30.05.' + m.group(2)
            courses_stared_year = int(m.group(1))
            courses_finished_year = int(m.group(2))

        m = re.search(r'(\d+).?.?класс', filename, re.IGNORECASE)
        if m:
            current_class = int(m.group(1))

        m = re.search(r'прием.(\d{4})|(\d{4}) год приема', filename, re.IGNORECASE)
        if m:
            admission_year = str(m.group(1))
            self.admission_date = '01.09.' + str(admission_year)

        if courses_stared_year is not None and current_class is not None and admission_year is not None:
            elapsed = courses_stared_year - int(admission_year) - 1
            admission_class = current_class - elapsed
            self.admission_class = f'{max(admission_class, int(self.admission_class))}'

        study_years = int(self.graduation_class) - int(self.admission_class)

        if admission_year is not None:
            self.admission_date = '01.09.' + str(admission_year)
            self.graduation_date = '30.05.' + str(int(admission_year) + study_years + 1)
        
    def __str__(self):
        return f"""
        graduation_date = {self.graduation_date}
        graduation_class = {self.graduation_class}
    
        admission_date = {self.admission_date}
        admission_class = {self.admission_class}
    
        courses_stared = {self.courses_stared}
        courses_finished = {self.courses_finished}
    
        department = {self.department}"""


def parse_ugly_do(sheet: Table, helper: UglyHelper) -> csv_data:
    lst = sheet_to_list2d(sheet)
    (row, col) = find_fio(lst)
    lst = list2d_crop_before_point(lst, row, col)
    lst = crop_list2d_csv_like(lst)
    csv = list2d_to_csv_data(lst, strip_str=True, lower_header=True, dedupe_key=True)

    result = []
    for rec in csv:
        try:
            base_rec = {
                'Фамилия': rec['фамилия'],
                'Имя': rec['имя'],
                'Отчество': rec['отчество'],
                'Глава': '',
                'Предмет': 'Не указан',
                'Место проведения': 'ЛНМО',
                'Начало': helper.courses_stared,
                'Завершение': helper.courses_finished,
                'Фамилия преподавателя': 'Преподаватель?',
                'Имя преподавателя': 'Преподаватель?',
                'Отчество преподавателя': 'Преподаватель?',
                'Экзамен': 'Нет'
            }
            overaly_rec = {}
            for field in rec:
                if field.find('дисциплина') >= 0:
                    if 'Название' in overaly_rec:  # Flush if already present
                        r = dict(base_rec)
                        r.update(overaly_rec)
                        result.append(r)
                        overaly_rec = {}
                    if rec[field]:
                        overaly_rec['Название'] = rec[field]
                elif field.find('количество часов') >= 0:
                    overaly_rec['Количество часов'] = rec[field] or '0'
                elif field.find('оценка') >= 0:
                    overaly_rec['Оценка/зачёт'] = rec[field]

                if len(overaly_rec) >= 3:  # Flush if collected enough info
                    r = dict(base_rec)
                    r.update(overaly_rec)
                    result.append(r)
                    overaly_rec = {}
        except Exception as e:
            tb = ''.join(traceback.format_exception(None, e, e.__traceback__))
            tb_tabbed = tb.replace('\n', '\n\t')
            print(f"Failed to parse record (do): {rec}",
                  f"\t{tb_tabbed}",
                  sep="\n"
              )

    return result


def parse_ugly_exams(sheet: Table, helper: UglyHelper) -> csv_data:
    lst = sheet_to_list2d(sheet)
    (row, col) = find_fio(lst)
    lst = list2d_crop_before_point(lst, row, col)
    lst = crop_list2d_csv_like(lst)
    csv = list2d_to_csv_data(lst, strip_str=True, lower_header=True, dedupe_key=True)

    result = []
    for rec in csv:
        try:
            base_rec = {
                'Фамилия': rec['фамилия'],
                'Имя': rec['имя'],
                'Отчество': rec['отчество'],
                'Глава': '',
                'Предмет': 'Не указан',
                'Место проведения': 'ЛНМО',
                'Начало': helper.courses_stared,
                'Завершение': helper.courses_finished,
                'Фамилия преподавателя': 'Преподаватель?',
                'Имя преподавателя': 'Преподаватель?',
                'Отчество преподавателя': 'Преподаватель?',
                'Экзамен': 'Да',
                'Количество часов': '0'
            }
            overaly_rec = {}
            for field in rec:
                if field.find('дисциплина') >= 0:
                    if 'Название' in overaly_rec:  # Flush if already present
                        r = dict(base_rec)
                        r.update(overaly_rec)
                        result.append(r)
                        overaly_rec = {}
                    if rec[field]:
                        overaly_rec['Название'] = rec[field]
                elif field.find('количество часов') >= 0:
                    overaly_rec['Количество часов'] = rec[field] or '0'
                elif field.find('оценка') >= 0:
                    overaly_rec['Оценка/зачёт'] = rec[field]

                if len(overaly_rec) >= 3:  # Flush if collected enough info
                    r = dict(base_rec)
                    r.update(overaly_rec)
                    result.append(r)
                    overaly_rec = {}
        except Exception as e:
            tb = ''.join(traceback.format_exception(None, e, e.__traceback__))
            tb_tabbed = tb.replace('\n', '\n\t')
            print(f"Failed to parse record (do): {rec}",
                  f"\t{tb_tabbed}",
                  sep="\n"
                  )
    return result


def parse_ugly_seminars(sheet: Table, helper: UglyHelper) -> csv_data:
    lst = sheet_to_list2d(sheet)
    (row, col) = find_fio(lst)
    lst = list2d_crop_before_point(lst, row, col)
    lst = crop_list2d_csv_like(lst)
    csv = list2d_to_csv_data(lst, strip_str=True, lower_header=True, dedupe_key=True)

    result = []
    for rec in csv:
        try:
            base_rec = {
                'Фамилия': rec['фамилия'],
                'Имя': rec['имя'],
                'Отчество': rec['отчество'],
                'Предмет': 'Не указан',
                'Место проведения': 'ЛНМО',
                'Начало': helper.courses_stared,
                'Завершение': helper.courses_finished,
                'Фамилия преподавателя': 'Преподаватель?',
                'Имя преподавателя': 'Преподаватель?',
                'Отчество преподавателя': 'Преподаватель?',
                'Оценка/зачёт': ''
            }
            overaly_rec = {}
            for field in rec:
                if field.find('название') >= 0:
                    if 'Название семинара' in overaly_rec:  # Flush if already present
                        r = dict(base_rec)
                        r.update(overaly_rec)
                        result.append(r)
                        overaly_rec = {}
                    if rec[field]:
                        overaly_rec['Название семинара'] = rec[field]
                elif field.find('количество часов') >= 0:
                    overaly_rec['Количество часов'] = rec[field] or '0'
                elif field.find('фамилия преподавателя') >= 0:
                    overaly_rec['Фамилия преподавателя'] = rec[field]
                elif field.find('имя преподавателя') >= 0:
                    overaly_rec['Имя преподавателя'] = rec[field]
                elif field.find('отчество преподавателя') >= 0:
                    overaly_rec['Отчество преподавателя'] = rec[field]

                if len(overaly_rec) >= 5:  # Flush if collected enough info
                    r = dict(base_rec)
                    r.update(overaly_rec)
                    result.append(r)
                    overaly_rec = {}
        except Exception as e:
            tb = ''.join(traceback.format_exception(None, e, e.__traceback__))
            tb_tabbed = tb.replace('\n', '\n\t')
            print(f"Failed to parse record (do): {rec}",
                  f"\t{tb_tabbed}",
                  sep="\n"
                  )
    return result


def parse_ugly_projects(sheet: Table, helper: UglyHelper) -> csv_data:
    lst = sheet_to_list2d(sheet)
    (row, col) = find_fio(lst)
    lst = list2d_crop_before_point(lst, row, col)
    lst = crop_list2d_csv_like(lst)
    csv = list2d_to_csv_data(lst, strip_str=True, lower_header=True, dedupe_key=True)

    result = []
    for rec in csv:
        try:
            base_rec = {
                'Фамилия': rec['фамилия'],
                'Имя': rec['имя'],
                'Отчество': rec['отчество'],
                'Предмет': 'Не указан',
                'Место проведения': 'ЛНМО',
                'Начало': helper.courses_stared,
                'Завершение': helper.courses_finished,
                'Фамилия руководителя': 'Преподаватель?',
                'Имя руководителя': 'Преподаватель?',
                'Отчество руководителя': 'Преподаватель?'
            }
            overaly_rec = {}
            for field in rec:
                if field.find('название') >= 0:
                    if 'Название проекта' in overaly_rec:  # Flush if already present
                        r = dict(base_rec)
                        r.update(overaly_rec)
                        result.append(r)
                        overaly_rec = {}
                    if rec[field]:
                        overaly_rec['Название проекта'] = rec[field]
                elif field.find('фамилия руков') >= 0 or field.find('фамилия преп') >= 0:
                    overaly_rec['Фамилия руководителя'] = rec[field]
                elif field.find('имя руков') >= 0 or field.find('имя преп') >= 0:
                    overaly_rec['Имя руководителя'] = rec[field]
                elif field.find('отчество руков') >= 0 or field.find('отчество преп') >= 0:
                    overaly_rec['Отчество руководителя'] = rec[field]

                if len(overaly_rec) >= 4:  # Flush if collected enough info
                    r = dict(base_rec)
                    r.update(overaly_rec)
                    result.append(r)
                    overaly_rec = {}
        except Exception as e:
            tb = ''.join(traceback.format_exception(None, e, e.__traceback__))
            tb_tabbed = tb.replace('\n', '\n\t')
            print(f"Failed to parse record (do): {rec}",
                  f"\t{tb_tabbed}",
                  sep="\n"
                  )
    return result


def parse_ugly_olympiads(sheet: Table, helper: UglyHelper) -> csv_data:
    lst = sheet_to_list2d(sheet)
    (row, col) = find_fio(lst)
    lst = list2d_crop_before_point(lst, row, col)
    lst = crop_list2d_csv_like(lst)
    csv = list2d_to_csv_data(lst, strip_str=True, lower_header=True, dedupe_key=True)

    result = []
    for rec in csv:
        try:
            base_rec = {
                'Фамилия': rec['фамилия'],
                'Имя': rec['имя'],
                'Отчество': rec['отчество'],
                'Место проведения': 'Неизвестно',
                'Начало': helper.courses_stared,
                'Завершение': helper.courses_finished,
                'Звание': '',
                'В составе команды': 'Нет',
                'Этап': ''
            }
            overaly_rec = {}
            for field in rec:
                if field.find('название') >= 0:
                    if 'Название конкурса / олимпиады' in overaly_rec:  # Flush if already present
                        r = dict(base_rec)
                        r.update(overaly_rec)
                        result.append(r)
                        overaly_rec = {}
                    if rec[field]:
                        overaly_rec['Название конкурса / олимпиады'] = rec[field]
                elif field.find('награда') >= 0:
                    overaly_rec['Награда'] = rec[field]

                if len(overaly_rec) >= 2:  # Flush if collected enough info
                    r = dict(base_rec)
                    r.update(overaly_rec)
                    result.append(r)
                    overaly_rec = {}
        except Exception as e:
            tb = ''.join(traceback.format_exception(None, e, e.__traceback__))
            tb_tabbed = tb.replace('\n', '\n\t')
            print(f"Failed to parse record (do): {rec}",
                  f"\t{tb_tabbed}",
                  sep="\n"
                  )
    return result


def parse_ugly_summer(sheet: Table, helper: UglyHelper) -> csv_data:
    lst = sheet_to_list2d(sheet)
    (row, col) = find_fio(lst)
    lst = list2d_crop_before_point(lst, row, col)
    lst = crop_list2d_csv_like(lst)
    csv = list2d_to_csv_data(lst, strip_str=True, lower_header=True, dedupe_key=True)

    result = []
    for rec in csv:
        try:
            fd = datetime.strptime(helper.courses_finished, '%d.%m.%Y')
            base_rec = {
                'Фамилия': rec['фамилия'],
                'Имя': rec['имя'],
                'Отчество': rec['отчество'],
                'Глава': '',
                'Предмет': 'Не указан',
                'Место проведения': 'Летняя школа',
                'Начало': f'01.06.{fd}',             # if helper.courses_finished - the date
                'Завершение': f'30.08.{fd}',
                'Фамилия преподавателя': 'Преподаватель?',
                'Имя преподавателя': 'Преподаватель?',
                'Отчество преподавателя': 'Преподаватель?',
                'Экзамен': 'Нет'
            }
            overaly_rec = {}
            for field in rec:
                if field.find('дисциплина') >= 0:
                    if 'Название' in overaly_rec:  # Flush if already present
                        r = dict(base_rec)
                        r.update(overaly_rec)
                        result.append(r)
                        overaly_rec = {}
                    if rec[field]:
                        overaly_rec['Название'] = rec[field]
                elif field.find('часов') >= 0:
                    overaly_rec['Количество часов'] = rec[field] or '0'
                elif field.find('оценка') >= 0:
                    overaly_rec['Оценка/зачёт'] = rec[field]
                elif str_has_words(field, 'фамилия преподавателя'):
                    overaly_rec['Фамилия преподавателя'] = rec[field]
                elif str_has_words(field, 'Имя преподавателя'):
                    overaly_rec['Имя преподавателя'] = rec[field]
                elif str_has_words(field, 'Отчество преподавателя'):
                    overaly_rec['Отчество преподавателя'] = rec[field]

                if len(overaly_rec) >= 6:  # Flush if collected enough info
                    r = dict(base_rec)
                    r.update(overaly_rec)
                    result.append(r)
                    overaly_rec = {}
        except Exception as e:
            tb = ''.join(traceback.format_exception(None, e, e.__traceback__))
            tb_tabbed = tb.replace('\n', '\n\t')
            print(f"Failed to parse record (do): {rec}",
                  f"\t{tb_tabbed}",
                  sep="\n"
                  )
    return result


def generate_ugly_educations(results: dict, helper: UglyHelper) -> list[dict]:
    names = set()
    result = []

    for t in ['course', 'seminar', 'project', 'olympiad']:
        if t in results:
            for r in results[t]:
                names.add( (r['Фамилия'], r['Имя'], r['Отчество']) )

    for n in names:
        rec = {
            'Фамилия': n[0],
            'Имя': n[1],
            'Отчество': n[2],
            'Площадка': helper.department,
            'Дата поступления': helper.admission_date,
            'Класс поступления': helper.admission_class,
            'Дата завершения': helper.graduation_date,
            'Класс завершения': helper.graduation_class,
            'Контактный телефон': '',
            'Контактный email': '',
        }
        result.append(rec)

    return result


def find_fio(data: list[list[str]]) -> (int, int):
    for y in range(len(data)):
        row = data[y]
        for x in range(len(row)):
            cell = row[x]
            if cell.strip().lower() == 'фамилия' and x + 2 < len(row):
                if row[x+1].strip().lower() == 'имя' and row[x+2].strip().lower() == 'отчество':
                    return (y, x)


def stitch_educations(edu_list):
    index = {}
    result = []
    for edu in edu_list:
        add_to_dict_multival(index, (edu['Фамилия'], edu['Имя'], edu['Отчество'] ), edu)

    for fio in index:
        edus_new = []
        edus_old = index[fio]
        edus_old.sort(
            key=lambda e: (
                datetime.strptime(e['Дата поступления'].strip(), "%d.%m.%Y").timestamp()
                if e['Дата поступления']
                else 0
            )
        )
        for edu in edus_old:
            if not edus_new:
                edus_new.append(edu)
                continue
            prev = edus_new[-1]
            curr = edu

            if prev['Площадка'] == curr['Площадка']:
                edus_new[-1]['Дата завершения'] = curr['Дата завершения']
                edus_new[-1]['Класс завершения'] = curr['Класс завершения']
                edus_new[-1]['Контактный телефон'] = curr['Контактный телефон']
                edus_new[-1]['Контактный email'] = curr['Контактный email']
        result += edus_new

    return result


def find_files(root_dir: str) -> list[str]:
    result = []
    for root, dirs, files in os.walk(root_dir):
        for f in files:
            p = pathlib.Path(root, f)
            result.append(p)
    return result