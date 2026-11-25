"""dpsso 路由：/api/dp/sso?ticket= 一次性票据换 session。"""

from django.urls import path

from .views import sso_ticket

app_name = "dpsso"
urlpatterns = [
    path("sso", sso_ticket, name="sso"),
]
