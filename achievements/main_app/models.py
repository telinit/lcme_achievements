from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    bio = models.TextField(max_length=500, blank=True)
    birth_date = models.DateField("Дата рождения", null=True, blank=True)
    middle_name = models.CharField("Отчество", max_length=255, blank=True)
    phone_number = models.CharField("Телефон", max_length=255, blank=True)

    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}"

    def get_education_department(self):
        deps = Education.objects \
            .filter(student=self.id) \
            .order_by(F('start_year') - F('finish_year'))

        dep = deps[0].department if deps else "(нет)"

        return dep

    def get_count_courses(self):
        return CourseParticipation.objects \
            .filter(student__id=self.id) \
            .count()

    def get_count_seminars(self):
        return SeminarParticipation.objects \
            .filter(student__id=self.id) \
            .count()

    def get_count_olympiads(self):
        return OlympiadParticipation.objects \
            .filter(student__id=self.id) \
            .count()

    def get_count_projects(self):
        return ProjectParticipation.objects \
            .filter(student__id=self.id) \
            .count()

    def __str__(self):
        return f"{self.username}: {self.full_name()}"


class Location(models.Model):
    name = models.CharField(verbose_name="Название", max_length=255, null=False, blank=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "местоположение"
        verbose_name_plural = "местоположения"


class Department(models.Model):
    name = models.CharField(verbose_name="Название", max_length=255, null=False, blank=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "площадка"
        verbose_name_plural = "площадки"


class Education(models.Model):
    student         = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Учащийся")
    department      = models.ForeignKey(Department, verbose_name="Площадка", on_delete=models.CASCADE)
    start_year      = models.IntegerField("Год начала обучения", )
    start_class     = models.IntegerField("Класс начала обучения", )
    finish_year     = models.IntegerField("Год окончания обучения", )
    finish_class    = models.IntegerField("Класс окончания обучения", )

    def __str__(self):
        return f"{self.student}, {self.department}: {self.start_year} класс, {self.start_class} год -- {self.finish_class} класс, {self.finish_year} год"

    class Meta:
        verbose_name = "обучение"
        verbose_name_plural = "обучения"


class Subject(models.Model):
    name = models.CharField(verbose_name="Название", max_length=255, null=False, blank=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "предмет"
        verbose_name_plural = "предметы"


class Activity(models.Model):
    name = models.CharField("Название", max_length=255)
    location = models.ForeignKey(Location, verbose_name="Место проведения", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name}, {self.location}"

    class Meta:
        verbose_name = "активность"
        verbose_name_plural = "активности"


class Course(Activity):
    chapter = models.CharField("Глава", max_length=255)
    subject = models.ForeignKey(Subject, verbose_name="Предмет", on_delete=models.CASCADE)
    default_hours = models.IntegerField("Стандартное кол-во часов", null=True)
    default_departments = models.ManyToManyField(Department, verbose_name="Стандартные площадки проведения")
    default_class = models.IntegerField("Стандартный класс проведения", null=True)

    def __str__(self):
        return f"К: {Activity.__str__(self)} - {self.subject} ({self.chapter})"

    class Meta:
        verbose_name = "курс"
        verbose_name_plural = "курсы"


class Seminar(Activity):
    subject = models.ForeignKey(Subject, verbose_name="Предмет, дисциплина", on_delete=models.CASCADE)

    def __str__(self):
        return f"С: {Activity.__str__(self)} - {self.subject}"

    class Meta:
        verbose_name = "семинар"
        verbose_name_plural = "семинары"


class Project(Activity):
    subject = models.ForeignKey(Subject, verbose_name="Предмет, дисциплина", on_delete=models.CASCADE)

    def __str__(self):
        return f"П: {Activity.__str__(self)} - {self.subject}"

    class Meta:
        verbose_name = "проект"
        verbose_name_plural = "проекты"


class Olympiad(Activity):
    stage = models.CharField("Этап олимпиады", max_length=255, null=True)

    def __str__(self):
        return f"О: {Activity.__str__(self)} - {self.stage}"

    class Meta:
        verbose_name = "олимпиада"
        verbose_name_plural = "олимпиады"


class Award(models.Model):
    title = models.CharField("Звание", max_length=255, null=True)
    prize = models.CharField("Награда", max_length=255, null=True)
    is_team_member = models.BooleanField("В составе команды", null=True)

    def __str__(self):
        return f"{self.title}, {self.prize}{', в составе команды' if self.is_team_member else ''}"

    class Meta:
        abstract = True
        verbose_name = "награда"
        verbose_name_plural = "награды"


class Participation(models.Model):
    student = models.ForeignKey(User, verbose_name="Учащийся", on_delete=models.CASCADE)
    started = models.DateTimeField("Начало участия", null=True)
    finished = models.DateTimeField("Конец участия")

    def __str__(self):
        return f"{self.student} ({self.started} - {self.finished})"

    class Meta:
        verbose_name = "участие"
        verbose_name_plural = "участия"


class CourseParticipation(Participation):
    course = models.ForeignKey(Course, verbose_name="Курс", on_delete=models.CASCADE)
    hours = models.IntegerField("Количество часов")
    teacher = models.ForeignKey(User, verbose_name="Преподаватель", related_name='course_teacher', on_delete=models.CASCADE)
    mark = models.CharField("Итоговая оценка", max_length=255)

    def __str__(self):
        return f"{Participation.__str__(self)}: {self.course}:  {self.mark}"

    class Meta:
        verbose_name = "участие в курсах"
        verbose_name_plural = "участия в курсах"


class SeminarParticipation(Participation):
    seminar = models.ForeignKey(Seminar, verbose_name="Семинар", on_delete=models.CASCADE)
    hours = models.IntegerField("Количество часов", null=True)
    teacher = models.ForeignKey(User, verbose_name="Преподаватель", related_name='seminar_teacher', on_delete=models.CASCADE)
    mark = models.CharField("Итоговая оценка", max_length=255, null=True)

    def __str__(self):
        return f"{Participation.__str__(self)}: {self.seminar}:  {self.teacher}"

    class Meta:
        verbose_name = "участие в семинарах"
        verbose_name_plural = "участия в семинарах"


class ProjectParticipation(Participation):
    project = models.ForeignKey(Project, verbose_name="Проект", on_delete=models.CASCADE)
    curator = models.ForeignKey(User, verbose_name="Руководитель", related_name='project_curator', on_delete=models.CASCADE)

    def __str__(self):
        return f"{Participation.__str__(self)}: {self.project}:  {self.curator}"

    class Meta:
        verbose_name = "участие в проектах"
        verbose_name_plural = "участия в проектах"


class OlympiadParticipation(Participation, Award):
    olympiad = models.ForeignKey(Olympiad, verbose_name="Олимпиада",  on_delete=models.CASCADE)

    def __str__(self):
        return f"{Participation.__str__(self)}: {self.olympiad}:  {Award.__str__(self)}"

    class Meta:
        verbose_name = "участие в олимпиадах"
        verbose_name_plural = "участия в олимпиадах"

