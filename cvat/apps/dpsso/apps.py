"""dpsso：data-pipeline 单点登录桥（Portal → CVAT 免密进入标注界面）。"""

from django.apps import AppConfig


class DpssoConfig(AppConfig):
    name = "cvat.apps.dpsso"
    label = "dpsso"
    verbose_name = "DP SSO Bridge"
