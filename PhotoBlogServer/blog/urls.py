from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register('Post', views.IntruderImage)
router.register('archive', views.ArchiveSummary, basename='archive')  # 편의 기능 2

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/new/', views.post_new, name='post_new'),
    path('post/<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('archive/', views.post_archive, name='post_archive'),  # 편의 기능 2
    path('archive/<int:year>/<int:month>/<int:day>/', views.post_archive_day, name='post_archive_day'),
    path('js_test/', views.js_test, name='js_test'),
    path('api_root/', include(router.urls)),
]