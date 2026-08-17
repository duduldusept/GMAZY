from django.urls import path
from . import views

urlpatterns = [
    path('declarer-panne/', views.declarer_panne, name='declarer_panne'),
]