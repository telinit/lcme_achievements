from django.urls import path

from . import views

urlpatterns = [
    path('', views.index),
    path('students', views.students),
    path('students/<int:id>', views.student_profile),
    path('courses', views.courses),
    path('courses/<int:id>/edit', views.courses_edit),
    path('import', views.import_),
    path('print', views.print_),
    path('print/dep/<int:dep>/year/<int:year>/<str:format_>', views.print_dep_year),
    path('tasks', views.tasks),
    path('tasks/dedupe_edu', views.dedupe_edu),
    path('tasks/find_similar_objects/<str:obj_type>/<str:method>/<int:limit>', views.find_similar_objects),
    path('print/student/<int:sid>/<str:format_>', views.student_report)
]

handler404 = 'main_app.views.p404'
