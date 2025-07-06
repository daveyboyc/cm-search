from django.urls import path
from . import views

app_name = 'trades'

urlpatterns = [
    path('', views.TradingAdvertListView.as_view(), name='list'),
    path('new/', views.TradingAdvertCreateView.as_view(), name='create'),
    path('<int:pk>/', views.TradingAdvertDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.TradingAdvertEditView.as_view(), name='edit'),
    path('<int:pk>/extend/', views.extend_advert_view, name='extend'),
    path('<int:pk>/message/', views.send_message_view, name='send_message'),
    path('<int:pk>/payment-success/', views.payment_success, name='payment_success'),
    path('<int:pk>/payment-cancel/', views.payment_cancel, name='payment_cancel'),
    path('<int:pk>/extension-success/', views.extension_success, name='extension_success'),
    path('<int:pk>/extension-cancel/', views.extension_cancel, name='extension_cancel'),
]