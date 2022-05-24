from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    bio = models.TextField(max_length=500, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    middle_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.username}: {self.last_name} {self.first_name} {self.middle_name}"


class Location(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Education(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    admission_year = models.IntegerField()
    admission_grade = models.IntegerField()
    graduation_year = models.IntegerField()
    graduation_class = models.IntegerField()

    def __str__(self):
        return f"{self.student}, {self.department}: {self.admission_grade} класс, {self.admission_year} год -- {self.graduation_class} класс, {self.graduation_year} год"


class Subject(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Activity(models.Model):
    name = models.CharField(max_length=255)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name}, {self.location}"


class Course(Activity):
    chapter = models.CharField(max_length=255)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    default_hours = models.IntegerField()
    default_departments = models.ManyToManyField(Department)
    default_grade = models.IntegerField()

    def __str__(self):
        return f"К: {Activity.__str__(self)} - {self.subject} ({self.chapter})"


class Seminar(Activity):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    def __str__(self):
        return f"С: {Activity.__str__(self)} - {self.subject}"


class Project(Activity):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    def __str__(self):
        return f"П: {Activity.__str__(self)} - {self.subject}"


class Olympiad(Activity):
    stage = models.CharField(max_length=255)

    def __str__(self):
        return f"О: {Activity.__str__(self)} - {self.stage}"


class Result(models.Model):
    pass


class Mark(Result):
    mark_value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.mark_value}"


class Award(Result):
    title = models.CharField(max_length=255)
    prize = models.CharField(max_length=255)
    is_team_member = models.BooleanField()

    def __str__(self):
        return f"{self.title}, {self.prize}{', в составе команды' if self.is_team_member else ''}"


class Participation(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    started = models.DateTimeField()
    finished = models.DateTimeField()
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, null=True)
    teacher = models.ForeignKey(User, related_name="common_participation_teacher", on_delete=models.CASCADE)
    result = models.ForeignKey(Result, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.activity} - {self.student}"

