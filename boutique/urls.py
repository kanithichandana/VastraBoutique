"""Customer storefront routes."""

from django.urls import path

from . import views

app_name = "boutique"

urlpatterns = [
    path("", views.storefront, name="storefront"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:pk>/", views.cart_remove, name="cart_remove"),
]
