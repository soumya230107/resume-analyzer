from django.contrib import admin
from django.urls import path
from analyzer import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.upload_resume, name='upload'),
]

