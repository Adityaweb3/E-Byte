from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path("", views.index , name='index'),
    path('product/<int:id>' , views.detail , name ='detail'),
    path('payment-success/<int:id>' , views.paymentSuccessful , name ='payment-success') , 
    path('payment-failed/<int:id>' , views.paymentFailed , name ='payment-failed') , 
    path('createproduct/' , views.create_product , name = 'createproduct'),
    path('editproduct/<int:id>/' , views.product_edit , name = 'editproduct'),
    path('delete/<int:id>/' , views.product_delete , name = 'delete'),
    path('dashboard/' , views.dashboard , name='dashboard') ,
    path('register/' , views.register , name='register'),
    path('login/' , auth_views.LoginView.as_view(template_name='myapp/login.html') , name='login'),
    path('logout/' , views.logout_user , name='logout'),
    path('invalid/' , views.invalid , name='invalid') ,
    path('purchases/' , views.my_purchase , name='purchases'),
    path('sales/' , views.sales , name='sales'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)