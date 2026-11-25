"""dpsso 视图：Portal 用户凭一次性票据换 CVAT session。

安全约束（B12a/FR-ANN 集成设计）：
- 票据 HMAC-SHA256 + exp≤60s + nonce 单次消费（cache.add 原子）；
- 绝不接受 data-pipeline 长期 bearer token 入 URL；
- next 仅允许站内相对路径（防 open redirect）；
- 角色映射：annotator→worker, qa→user, admin→admin（取最高权限）。
"""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.views.decorators.http import require_GET

from .ticket import TicketError, verify_ticket

logger = logging.getLogger(__name__)

# data-pipeline 标注角色 → CVAT 全局组（权限升序）。
ROLE_MAP = {"annotator": "worker", "qa": "user", "admin": "admin"}
ROLE_PRIORITY = ["worker", "user", "admin"]
NONCE_TTL = 120  # nonce 防重放窗口（>票据有效期）


def _cvat_group(roles: list) -> str:
    """取映射后最高权限组；无匹配 → worker（最低权限兜底，不可标注管理）。"""
    best = "worker"
    for r in roles or []:
        g = ROLE_MAP.get(str(r))
        if g and ROLE_PRIORITY.index(g) > ROLE_PRIORITY.index(best):
            best = g
    return best


def _safe_next(nxt: str) -> str:
    """next 白名单：站内相对路径，拒绝 // 与反斜杠规避。"""
    if nxt and nxt.startswith("/") and not nxt.startswith("//") and "\\" not in nxt:
        return nxt
    return "/"


@require_GET
def sso_ticket(request):
    secret = getattr(settings, "DP_SSO_SECRET", "")
    if not secret:
        return HttpResponseForbidden("dp sso disabled")
    ticket = request.GET.get("ticket", "")
    try:
        payload = verify_ticket(secret, ticket)
    except TicketError as e:
        logger.warning("dpsso ticket rejected: %s", e)
        return HttpResponseForbidden("invalid sso ticket")
    # nonce 单次性：cache.add 原子占坑，已存在即重放。
    if not cache.add(f"dpsso:{payload['nonce']}", 1, timeout=NONCE_TTL):
        return HttpResponseForbidden("ticket replayed")

    User = get_user_model()
    uid = str(payload["uid"])
    # dp-u- 前缀：与服务账号 dp-annotation 隔离命名空间——
    # uid="annotation" 不得解析到服务账号（防提权）。
    username = f"dp-u-{uid}"
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": payload.get("email", "") or "",
            "first_name": (payload.get("name") or "")[:150],
        },
    )
    changed = False
    if payload.get("email") and user.email != payload["email"]:
        user.email = payload["email"]
        changed = True
    if payload.get("name") and user.first_name != payload["name"]:
        user.first_name = payload["name"][:150]
        changed = True
    group_name = _cvat_group(payload.get("roles") or [])
    group, _ = Group.objects.get_or_create(name=group_name)
    if created or not user.groups.filter(name=group_name).exists():
        user.groups.set([group])
        changed = True
    if changed or created:
        user.save()
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return HttpResponseRedirect(_safe_next(payload.get("next") or "/"))
