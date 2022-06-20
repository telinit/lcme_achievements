import pathlib
import random
import tempfile
from datetime import datetime
from io import StringIO, BytesIO
from typing import List, Iterable, Any

from PyPDF2 import PdfReader
from odf.draw import Frame, Image
from odf.element import Element
from odf.opendocument import OpenDocumentText
from odf.style import Style, TextProperties, GraphicProperties, PageLayoutProperties, PageLayout, MasterPage, \
    ParagraphProperties, TableCellProperties, TableColumnProperties, TableProperties
from odf.table import Table, TableRow, TableCell, TableColumn
from odf.text import P, LineBreak, SoftPageBreak
from relatorio.templates.opendocument import Template
import os

from ..models import *


static_path = pathlib.Path(
        pathlib.Path(__file__).parent.parent,
        'static'
    )


def strings_to_paragraphs(l: List[str], style):
    res = []
    for s in l:
        p = P(stylename=style)
        p.addText(s)
        res.append(p)

    return res


def strings_to_breaks(l: List[str], style, prefix="", suffix="", sep=""):
    p = P(stylename=style, text=prefix)
    for i in range(len(l)):
        if i != 0:
            p.addText(sep)
            p.addElement(LineBreak())
        p.addText(l[i])

    p.addText(suffix)
    return p


def add_elements(node: Element, lst: Iterable[Element]) -> None:
    for x in lst:
        node.addElement(x)


def make_table(
        data: Iterable[Iterable[str]],
        column_width: Iterable[str] = None,
        doc: OpenDocumentText = None,
        table_style=None,
        header_style=None,
        row_style=None,
        cell_style=None,
        p_style=None,
        p_style_header=None
    ) -> Table:

    table_name=f"Table_{random.randbytes(8).hex()}"
    table = Table(stylename=table_style)
    row_is_first = True
    for row in data:
        t_row = TableRow(stylename=header_style if row_is_first else row_style)
        cell_is_first = True
        for cell in row:
            final_cell_style = cell_style
            if (not cell_style) and row_is_first and cell_is_first:
                final_cell_style = doc.src_styles['auto_styles']['first_table_cell']
            elif (not cell_style) and (not row_is_first) and cell_is_first:
                final_cell_style = doc.src_styles['auto_styles']['left_table_cell']
            elif (not cell_style) and row_is_first and (not cell_is_first):
                final_cell_style = doc.src_styles['auto_styles']['top_table_cell']
            elif not cell_style:
                final_cell_style = doc.src_styles['auto_styles']['default_table_cell']
            t_cell = TableCell(stylename=final_cell_style)
            t_cell.addElement(
                P(text=cell, stylename=p_style_header if p_style_header and row_is_first else p_style )
            )
            t_row.addElement(t_cell)
            cell_is_first = False
        if row_is_first:
            if column_width and doc:
                for cw in column_width:
                    column_name = f"{table_name}_Column_{random.randbytes(8).hex()}"
                    style = Style(
                        name=column_name,
                        family="table-column"
                    )
                    style.addElement(
                        TableColumnProperties(
                            columnwidth=cw
                        )
                    )
                    doc.automaticstyles.addElement(style)
                    table.addElement(
                        TableColumn(
                            stylename=style
                        )
                    )
            else:
                table.addElement(
                    TableColumn(
                        numbercolumnsrepeated=len(row)
                    )
                )
            row_is_first = False
        table.addElement(t_row)

    return table


def make_styles():
    styles = {}
    master_styles = {}
    auto_styles = {}

    pagelayout = PageLayout(name="PageLayout")
    pagelayout.addElement(
        PageLayoutProperties(
            margin="1cm",
            pagewidth="14.80cm",
            pageheight="21.00cm",
            printorientation="portrait"
        )
    )

    masterpage = MasterPage(
        name="Standard",
        pagelayoutname=pagelayout
    )

    body = Style(name="Standard", family="paragraph")
    body.addElement(
        TextProperties(
            attributes={
                'fontsize': "10pt",
                'fontfamily': "Lato",
            }
        )
    )

    h1 = Style(name="Heading 1", family="paragraph", parentstylename=body)
    h1.addElement(
        TextProperties(
            attributes={
                'fontsize': "14pt",
                'fontweight': "bold",
                'fontfamily': "Lato",
            }
        )
    )

    h2 = Style(name="Heading 2", family="paragraph", parentstylename=body)
    h2.addElement(
        TextProperties(
            attributes={
                'fontsize': "12pt",
                'fontweight': "bold",
                'fontfamily': "Lato"
            }
        )
    )

    h1_title = Style(name="Heading 1 T", family="paragraph", parentstylename=h1)
    h1_title.addElement(
        ParagraphProperties(
            textalign="center",
            marginbottom = "5mm"
        )
    )

    h2_title = Style(name="Heading 2 T", family="paragraph", parentstylename=h2)
    h2_title.addElement(
        ParagraphProperties(
            textalign="center",
            marginbottom="3mm"
        )
    )

    body_title = Style(name="Text Body T", family="paragraph", parentstylename=body)
    body_title.addElement(
        ParagraphProperties(textalign="center")
    )

    body_bold = Style(name="Text Body Bold", family="paragraph", parentstylename=body)
    body_bold.addElement(
        TextProperties(
            attributes={
                'fontweight': "bold",
            }
        )
    )

    logo = Style(name='Logo', parentstylename="Graphics", family="graphic")
    logo.addElement(
        GraphicProperties(
            verticalpos="from-top",
            verticalrel="page",
            horizontalpos="from-left",
            horizontalrel="page"
        )
    )

    break_before = Style(name='Break Before', family="paragraph")
    break_before.addElement(
        ParagraphProperties(
            breakbefore="page"
        )
    )

    break_after = Style(name='Break After', family="paragraph")
    break_before.addElement(
        ParagraphProperties(
            breakafter="page"
        )
    )

    h1_title_break_before = Style(name="Heading 1 T Break", family="paragraph", parentstylename=h1_title)
    h1_title_break_before.addElement(
        ParagraphProperties(
            breakbefore="page"
        )
    )

    default_table_cell = Style(name="Table Cell D", family="table-cell")
    default_table_cell.addElement(
        TableCellProperties(
            borderright="0.5pt solid #000000",
            borderbottom="0.5pt solid #000000",
        )
    )

    left_table_cell = Style(name="Table Cell Left D", family="table-cell")
    left_table_cell.addElement(
        TableCellProperties(
            borderleft="0.5pt solid #000000",
            borderright="0.5pt solid #000000",
            borderbottom="0.5pt solid #000000",
        )
    )

    top_table_cell = Style(name="Table Cell Top D", family="table-cell")
    top_table_cell.addElement(
        TableCellProperties(
            borderright="0.5pt solid #000000",
            borderbottom="0.5pt solid #000000",
            bordertop="0.5pt solid #000000",
        )
    )

    first_table_cell = Style(name="Table Cell First D", family="table-cell")
    first_table_cell.addElement(
        TableCellProperties(
            borderleft="0.5pt solid #000000",
            borderright="0.5pt solid #000000",
            borderbottom="0.5pt solid #000000",
            bordertop="0.5pt solid #000000",
        )
    )

    cell_underline = Style(name="Table Cell Underlined", family="table-cell")
    cell_underline.addElement(
        TableCellProperties(
            borderbottom="0.5pt solid #000000",
        )
    )

    # default_table = Style(name="Table D", family="table")
    # default_table.addElement(
    #     TableProperties(
    #         borderright="0.5pt solid #000000",
    #         borderbottom="0.5pt solid #000000"
    #     )
    # )

    styles['h1'] = h1
    styles['h2'] = h2
    styles['body'] = body
    styles['body_bold'] = body_bold
    styles['logo'] = logo
    styles['h1_title'] = h1_title
    styles['h2_title'] = h2_title
    styles['body_title'] = body_title
    styles['break_before'] = break_before
    styles['break_after'] = break_after
    styles['h1_title_break_before'] = h1_title_break_before
    auto_styles['default_table_cell'] = default_table_cell
    auto_styles['left_table_cell'] = left_table_cell
    auto_styles['top_table_cell'] = top_table_cell
    auto_styles['first_table_cell'] = first_table_cell
    auto_styles['cell_underline'] = cell_underline
    auto_styles['pagelayout'] = pagelayout
    master_styles['masterpage'] = masterpage

    return {
        'styles': styles,
        'auto_styles': auto_styles,
        'master_styles': master_styles,
    }


def write_styles(doc: OpenDocumentText, styles):
    for s in styles['master_styles']:
        doc.masterstyles.addElement(styles['master_styles'][s])

    for s in styles['auto_styles']:
        doc.automaticstyles.addElement(styles['auto_styles'][s])

    for s in styles['styles']:
        doc.styles.addElement(styles['styles'][s])

    doc.src_styles = styles


def write_title(student_id: int, doc: OpenDocumentText):
    # Logo
    logo_path = pathlib.Path(
        static_path,
        'logo_lnmo.png'
    ).resolve()
    logo = doc.addPicture(str(logo_path))
    logo_frame = Frame(
        width="4.92cm",
        height="4.26cm",
        # x="5cm",
        # y="1cm",
        anchortype="as-char",
        stylename=doc.src_styles['styles']['logo']
    )
    logo_frame.addElement(Image(href=logo))
    logo_paragraph = P(stylename=doc.src_styles['styles']['body_title'])
    logo_paragraph.addElement(logo_frame)
    doc.text.addElement(logo_paragraph)

    # First heading
    t1 = ["",
          "",
          "",
          "",
          "ИНДИВИДУАЛЬНЫЕ ДОСТИЖЕНИЯ",
         "в области дополнительного образования,",
         "проектной и исследовательской деятельности",
         "",
         "(зачетная книжка)"]

    t1_p = strings_to_breaks(t1, doc.src_styles['styles']['h2_title'])
    doc.text.addElement(t1_p)

    t2 = ["",
          "",
          "учащегося частного общеобразовательного учреждения дополнительного образования",
         "«ЛАБОРАТОРИЯ НЕПРЕРЫВНОГО МАТЕМАТИЧЕСКОГО ОБРАЗОВАНИЯ»",
          ""]

    t2_p = strings_to_breaks(t2, doc.src_styles['styles']['body_title'])
    doc.text.addElement(t2_p)

    edus = Education.objects.filter(student__id=student_id)

    t3 = list(map(lambda e: e.department.name, edus))

    if len(t3) == 0:
        t3 = ['Без обучения по направлениям']

    t3_p = strings_to_breaks(t3, doc.src_styles['styles']['body_title'], prefix="(", suffix=")", sep=",")

    doc.text.addElement(t3_p)

    student = User.objects.get(pk=student_id)
    edu_start = min(map(lambda e: e.start_date.year, edus))
    edu_finish = max(map(lambda e: e.finish_date.year, edus))

    t4_p = strings_to_breaks(
        [
            "",
            f"{student.last_name} {student.first_name} {student.middle_name}",
            f"выпуск {edu_finish} года"
        ], doc.src_styles['styles']['h1_title'])

    doc.text.addElement(t4_p)

    y = datetime.now().year

    t5_p = strings_to_breaks(
        [
            "",
            "",
            "",
            "",
            "",
            f"{edu_start}-{edu_finish} годы",
            f"Номер документа: {student_id:04d}-{y}",
            f"Год выдачи: {y} год",
            "г. Санкт-Петербург"
        ],
        doc.src_styles['styles']['body_title']
    )

    doc.text.addElement(t5_p)


def write_do(student_id: int, doc: OpenDocumentText):
    doc.text.addElement(P(text="Освоенные курсы дополнительного образования", stylename=doc.src_styles['styles']['h1_title_break_before']))

    have_data = False

    educations: Iterable[Education] = Education.objects.filter(student__id=student_id)

    for edu in educations:
        courses = CourseParticipation.objects\
            .filter(
                student__id=student_id,
                started__gte=edu.start_date,
                started__lte=edu.finish_date,
            ).exclude(
                course__location__name="Летняя школа"
            )

        if not courses:
            continue
        else:
            have_data = True

        courses_grouped = {}
        for crs in courses:
            education_year = crs.started.year
            if 1 <= crs.started.month <= 8:
                education_year -= 1

            if education_year in courses_grouped:
                courses_grouped[education_year].append(crs)
            else:
                courses_grouped[education_year] = [crs]

        course_years = list(courses_grouped.keys())
        course_years.sort()

        # print(f"student_id = {student_id}")
        # print(f"course_years = {course_years}")

        min_year = course_years[0]

        for year in course_years:
            doc.text.addElement(
                strings_to_breaks(
                    [
                        "",
                        f"{year}-{year+1} учебный год, {year-min_year+1} год обучения, {edu.department.name.lower()}"
                    ], doc.src_styles['styles']['h2_title'])
            )
            table_data = [['Предмет','Часы','Оценка']]
            for c in courses_grouped[year]:
                table_data.append([c.course.name, c.hours, c.mark])

            doc.text.addElement(
                make_table(
                    table_data,
                    doc=doc,
                    column_width=['9cm', '2cm', '2cm'],
                    p_style_header=doc.src_styles['styles']['body_bold']
                )
            )
    if not have_data:
        doc.text.addElement(P(text="Нет данных", stylename=doc.src_styles['styles']['body_title']))


def write_summer_school(student_id: int, doc: OpenDocumentText):
    doc.text.addElement(P(text="Участие в работе Летней научной школы ЛНМО", stylename=doc.src_styles['styles']['h1_title_break_before']))

    have_data = False

    educations: Iterable[Education] = Education.objects.filter(student__id=student_id)

    for edu in educations:
        courses = CourseParticipation.objects \
            .filter(
            student__id=student_id,
            started__gte=edu.start_date,
            started__lte=edu.finish_date,
            course__location__name="Летняя школа"
        )

        if not courses:
            continue
        else:
            have_data = True

        courses_grouped: dict[CourseParticipation] = {}
        for crs in courses:
            education_year = crs.started.year
            if 1 <= crs.started.month <= 8:
                education_year -= 1

            if education_year in courses_grouped:
                courses_grouped[education_year].append(crs)
            else:
                courses_grouped[education_year] = [crs]

        course_years = list(courses_grouped.keys())
        course_years.sort()

        min_year = course_years[0]

        for year in course_years:
            doc.text.addElement(
                strings_to_breaks(
                    [
                        "",
                        f"{year}-{year + 1} учебный год, {year - min_year + 1} год обучения, {edu.department.name.lower()}"
                    ], doc.src_styles['styles']['h2_title'])
            )
            table_data = [['Название','Часы','Оценка','ФИО преподавателя']]
            for c in courses_grouped[year]:
                table_data.append([
                    c.course.name,
                    c.hours,
                    c.mark,
                    f"{c.teacher.last_name} {c.teacher.first_name} {c.teacher.middle_name}"
                ])

            doc.text.addElement(
                make_table(
                    table_data,
                    doc=doc,
                    column_width=['6cm', '1cm', '1cm', '9cm'],
                    p_style_header=doc.src_styles['styles']['body_bold']
                )
            )

    if not have_data:
        doc.text.addElement(P(text="Нет данных", stylename=doc.src_styles['styles']['body_title']))


def write_seminars(student_id: int, doc: OpenDocumentText):
    doc.text.addElement(P(text="Участие в работе научных семинаров, проектных групп", stylename=doc.src_styles['styles']['h1_title_break_before']))

    have_data = False

    educations: Iterable[Education] = Education.objects.filter(student__id=student_id)

    for edu in educations:
        seminars = SeminarParticipation.objects \
            .filter(
                student__id=student_id,
                started__gte=edu.start_date,
                started__lte=edu.finish_date
            )

        if not seminars:
            continue
        else:
            have_data = True

        seminars_grouped: dict[SeminarParticipation] = {}
        for crs in seminars:
            education_year = crs.started.year
            if 1 <= crs.started.month <= 8:
                education_year -= 1

            if education_year in seminars_grouped:
                seminars_grouped[education_year].append(crs)
            else:
                seminars_grouped[education_year] = [crs]

        seminar_years = list(seminars_grouped.keys())
        seminar_years.sort()

        min_year = seminar_years[0]

        for year in seminar_years:
            doc.text.addElement(
                strings_to_breaks(
                    [
                        "",
                        f"{year}-{year + 1} учебный год, {year - min_year + 1} год обучения, {edu.department.name.lower()}"
                    ], doc.src_styles['styles']['h2_title'])
            )
            table_data = [['Название','ФИО преподавателя']]
            for c in seminars_grouped[year]:
                table_data.append([
                    c.seminar.name,
                    f"{c.teacher.last_name} {c.teacher.first_name} {c.teacher.middle_name}"
                ])

            doc.text.addElement(
                make_table(
                    table_data,
                    doc=doc,
                    column_width=['8.5cm', '8.5cm'],
                    p_style_header=doc.src_styles['styles']['body_bold']
                )
            )

    if not have_data:
        doc.text.addElement(P(text="Нет данных", stylename=doc.src_styles['styles']['body_title']))


def write_projects(student_id: int, doc: OpenDocumentText):
    doc.text.addElement(P(text="Научное исследование (проект), выполненный в рамках "
                               "научного семинара или проектной группы "
                               "ЧОУ ОиДО «ЛНМО» или в сторонних организациях", stylename=doc.src_styles['styles']['h1_title_break_before']))

    have_data = False

    educations: Iterable[Education] = Education.objects.filter(student__id=student_id)

    for edu in educations:
        projects = ProjectParticipation.objects \
            .filter(
            student__id=student_id,
            started__gte=edu.start_date,
            started__lte=edu.finish_date
        )

        if not projects:
            continue
        else:
            have_data = True

        projects_grouped: dict[int, list[ProjectParticipation]] = {}
        for proj in projects:
            education_year = proj.started.year
            if 1 <= proj.started.month <= 8:
                education_year -= 1

            if education_year in projects_grouped:
                projects_grouped[education_year].append(proj)
            else:
                projects_grouped[education_year] = [proj]

        project_years: list[int] = list(projects_grouped.keys())
        project_years.sort()

        min_year = project_years[0]

        for year in project_years:
            doc.text.addElement(
                strings_to_breaks(
                    [
                        "",
                        f"{year}-{year + 1} учебный год, {year - min_year + 1} год обучения, {edu.department.name.lower()}"
                    ], doc.src_styles['styles']['h2_title'])
            )
            table_data = [['Название','ФИО руководителя']]
            for p in projects_grouped[year]:
                table_data.append([
                    p.project.name,
                    f"{p.curator.last_name} {p.curator.first_name} {p.curator.middle_name}"
                ])

            doc.text.addElement(
                make_table(
                    table_data,
                    doc=doc,
                    column_width=['8.5cm', '8.5cm'],
                    p_style_header=doc.src_styles['styles']['body_bold']
                )
            )

    if not have_data:
        doc.text.addElement(P(text="Нет данных", stylename=doc.src_styles['styles']['body_title']))


def write_olympiads(student_id: int, doc: OpenDocumentText):
    doc.text.addElement(P(text="Достижения на конкурсах, олимпиадах, турнирах", stylename=doc.src_styles['styles']['h1_title_break_before']))

    have_data = False

    educations: Iterable[Education] = Education.objects.filter(student__id=student_id)

    for edu in educations:
        olympiads = OlympiadParticipation.objects \
            .filter(
            student__id=student_id,
            started__gte=edu.start_date,
            started__lte=edu.finish_date
        )

        if not olympiads:
            continue
        else:
            have_data = True

        olympiads_grouped: dict[int, list[ProjectParticipation]] = {}
        for oly in olympiads:
            education_year = oly.started.year
            if 1 <= oly.started.month <= 8:
                education_year -= 1

            if education_year in olympiads_grouped:
                olympiads_grouped[education_year].append(oly)
            else:
                olympiads_grouped[education_year] = [oly]

        olympiad_years: list[int] = list(olympiads_grouped.keys())
        olympiad_years.sort()

        min_year = olympiad_years[0]

        for year in olympiad_years:
            doc.text.addElement(
                strings_to_breaks(
                    [
                        "",
                        f"{year}-{year + 1} учебный год, {year - min_year + 1} год обучения, {edu.department.name.lower()}"
                    ], doc.src_styles['styles']['h2_title'])
            )
            table_data = [['Название','Награда']]
            for o in olympiads_grouped[year]:
                table_data.append([
                    o.olympiad.name + (f", {o.olympiad.stage}" if o.olympiad.stage else ""),
                    o.title + (f", {o.prize}" if o.prize else "") + (f", в составе команды" if o.is_team_member else "")
                ])

            doc.text.addElement(
                make_table(
                    table_data,
                    doc=doc,
                    column_width=['8.5cm', '8.5cm'],
                    p_style_header=doc.src_styles['styles']['body_bold']
                )
            )

    if not have_data:
        doc.text.addElement(P(text="Нет данных", stylename=doc.src_styles['styles']['body_title']))


def write_padding(n: int, doc: OpenDocumentText):
    if n < 1:
        return

    def pad_first():
        doc.text.addElement(P(text="Примечания", stylename=doc.src_styles['styles']['h1_title_break_before']))
        t1 = make_table(
            map(lambda i: [''], range(39)),
            cell_style=doc.src_styles['auto_styles']['cell_underline'],
            doc=doc
        )
        doc.text.addElement(t1)

    def pad_middle():
        for i in range(n-1):
            doc.text.addElement(P(text=" ",stylename=doc.src_styles['styles']['break_before']))
            tn = make_table(
                map(lambda i: [''], range(41)),
                cell_style=doc.src_styles['auto_styles']['cell_underline'],
                doc=doc
            )
            doc.text.addElement(tn)

    def pad_last():
        logo_path = pathlib.Path(
            static_path,
            'logo_lnmo.png'
        ).resolve()
        logo = doc.addPicture(str(logo_path))
        logo_frame = Frame(
            width="4.92cm",
            height="4.26cm",
            # x="5cm",
            # y="1cm",
            anchortype="as-char",
            stylename=doc.src_styles['styles']['logo']
        )
        logo_frame.addElement(Image(href=logo))

        logo_style_end = Style(
            name="logo_style_end",
            parentstylename=doc.src_styles['styles']['body_title'],
            family="paragraph",
            ##
        )
        logo_style_end.addElement(
            ParagraphProperties(
                margintop="7cm",
                breakbefore="page"
            )
        )
        doc.styles.addElement(logo_style_end)

        logo_paragraph = P(stylename=logo_style_end)
        logo_paragraph.addElement(logo_frame)

        doc.text.addElement(logo_paragraph)

    if n > 1:
        pad_first()
    for i in range(n - 2):
        pad_middle()
    pad_last()


def document_to_odt_data(doc: OpenDocumentText):
    buff = BytesIO()
    doc.save(buff)
    buff.seek(0)

    return buff


def odt_data_to_pdf_reader(odt: BytesIO) -> PdfReader:
    odt.seek(0)
    tmp = tempfile.NamedTemporaryFile(suffix=".odt", delete=False)
    tmp.write(odt.read())
    tmp.flush()
    tmp.close()
    tmp_path = pathlib.Path(tmp.name)
    os.chdir(tmp_path.parent)
    os.system(f"soffice --headless --convert-to pdf {tmp_path.name}")
    reader = PdfReader(tmp_path.with_suffix('.pdf'))

    return reader


def document_get_missing_padding_count(doc: OpenDocumentText) -> int:
    data = document_to_odt_data(doc)
    pdf_r = odt_data_to_pdf_reader(data)
    n_rem = pdf_r.numPages % 4

    return 4 - n_rem


def generate_document_for_student(id: int, document: OpenDocumentText = None):
    report = document or OpenDocumentText()

    if not document:
        styles = make_styles()
        write_styles(report, styles)
    write_title(id, report)
    write_do(id, report)
    write_summer_school(id, report)
    write_seminars(id, report)
    write_projects(id, report)
    write_olympiads(id, report)

    pad = document_get_missing_padding_count(report)
    write_padding(pad, report)

    return report


def generate_document_for_many_students(stud_list: Iterable[int], document: OpenDocumentText = None):
    report = document

    for sid in stud_list:
        report = generate_document_for_student(sid, report)
        report.text.addElement(P(text=" ",stylename=report.src_styles['styles']['break_before']))

    return report

