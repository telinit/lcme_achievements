from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    birth_date = models.DateField(null=True, blank=True)
    middle_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.user.__str__()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Location(models.Model):
    name = models.CharField(max_length=255)


class Department(models.Model):
    name = models.CharField(max_length=255)


class Education(models.Model):
    student = models.ForeignKey(Profile, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    admission_year = models.IntegerField()
    admission_grade = models.IntegerField()
    graduation_year = models.IntegerField()
    graduation_class = models.IntegerField()


class Subject(models.Model):
    name = models.CharField(max_length=255)


class Activity(models.Model):
    name = models.CharField(max_length=255)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)


class Course(Activity):
    chapter = models.CharField(max_length=255)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    default_hours = models.IntegerField()
    default_departments = models.ManyToManyField(Department)
    default_grade = models.IntegerField()


class Seminar(Activity):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)


class Project(Activity):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)


class Olympiad(Activity):
    stage = models.CharField(max_length=255)


class Result(models.Model):
    class Meta:
        abstract = True


class Mark(Result):
    mark = models.CharField(max_length=255)


class Award(Result):
    title = models.CharField(max_length=255)
    prize = models.CharField(max_length=255)
    is_team_member = models.BooleanField()


class Participation(models.Model):
    student = models.ForeignKey(Profile, on_delete=models.CASCADE)
    started = models.DateTimeField(auto_now=True)
    finished = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OlympiadParticipation(Participation):
    award = models.ForeignKey(Award, on_delete=models.CASCADE)


class CommonParticipation(Participation):
    teacher = models.ForeignKey(Profile, related_name="common_participation_teacher", on_delete=models.CASCADE)
    mark = models.ForeignKey(Mark, on_delete=models.CASCADE)

