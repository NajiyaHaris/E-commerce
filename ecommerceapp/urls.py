from . import views
from django.urls import path

urlpatterns=[
    path('',views.home,name='home'),
    path('register/',views.register,name='register'),
    path('login/',views.login,name='login'),
    path('logout/',views.logout,name='logout'),
    path("cart/",views.cart,name="cart"),
    path("add/<int:product_id>/",views.add_to_cart,name="add_to_cart"),
    path("remove/<int:item_id>/",views.remove_from_cart,name="remove_from_cart"),
    path("decrease/<int:item_id>/",views.decrease_quantity,name="decrease_quantity"),
    path("checkout/",views.checkout,name="checkout"),
    path("checkout/success/<int:order_id>/",views.checkout_success,name="checkout_success"),
    path('product/<int:item_id>/',views.detail,name='detail'),
]