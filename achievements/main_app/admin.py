from django.contrib import admin

from .models import *


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'first_name', 'middle_name', 'last_name']
    # list_filter = ('first_name',)
    search_fields = ['username', 'first_name', 'middle_name', 'last_name']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name']
    # list_filter = ('first_name',)
    search_fields = ['name']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name']
    # list_filter = ('first_name',)
    search_fields = ['name']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name']
    # list_filter = ('first_name',)
    search_fields = ['name']


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ['student', 'department', 'start_date', 'finish_date']
    list_filter = ('department', 'start_date', 'finish_date')
    search_fields = [
        'student__first_name',
        'student__last_name',
        'student__middle_name',
        'student__username',
        'department__name',
        'start_date',
        'finish_date'
    ]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'chapter', 'location', 'subject']
    list_filter = ('location', 'subject')
    search_fields = ['name', 'chapter', 'location__name', 'subject__name']
    fieldsets = (
        (None, {
            'fields': ('name', 'location', 'chapter', 'subject')
        }),
        ('Значения по умолчанию для автоматических участий в курсе', {
            'classes': ('collapse',),
            'fields': ('default_hours', 'default_departments', 'default_class'),
        }),
    )


@admin.register(Seminar)
class SeminarAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'subject']
    list_filter = ('location', 'subject')
    search_fields = ['name', 'location__name', 'subject__name']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'subject']
    list_filter = ('location', 'subject')
    search_fields = ['name', 'location__name', 'subject__name']


@admin.register(Olympiad)
class OlympiadAdmin(admin.ModelAdmin):
    list_display = ['name', 'stage', 'location']
    list_filter = ('location', 'stage')
    search_fields = ['name', 'location__name', 'stage']


@admin.register(CourseParticipation)
class CourseParticipationAdmin(admin.ModelAdmin):
    list_display = ['student', 'started', 'finished', 'course', 'teacher', 'mark']
    list_filter = ('started', 'finished', 'course', 'mark')
    search_fields = [
        'student__first_name',
        'student__middle_name',
        'student__last_name',
        'student__username',
        'started',
        'finished',
        'course__name'
    ]


@admin.register(SeminarParticipation)
class SeminarParticipationAdmin(admin.ModelAdmin):
    list_display = ['student', 'started', 'finished', 'seminar', 'teacher', 'mark']
    list_filter = ('started', 'finished', 'seminar', 'mark')
    search_fields = [
        'student__first_name',
        'student__middle_name',
        'student__last_name',
        'student__username',
        'started',
        'finished',
        'seminar__name'
    ]


@admin.register(ProjectParticipation)
class ProjectParticipationAdmin(admin.ModelAdmin):
    list_display = ['student', 'started', 'finished', 'project', 'curator']
    list_filter = ('started', 'finished', 'curator')
    search_fields = [
        'student__first_name',
        'student__middle_name',
        'student__last_name', 
        'student__username', 
        'started', 
        'finished',
        'project__name'
    ]


@admin.register(OlympiadParticipation)
class OlympiadParticipationAdmin(admin.ModelAdmin):
    list_display = ['student', 'started', 'finished', 'olympiad']
    list_filter = ('started', 'finished', 'olympiad')
    search_fields = [
        'student__first_name',
        'student__middle_name',
        'student__last_name',
        'student__username',
        'started',
        'finished',
        'olympiad__name'
    ]






