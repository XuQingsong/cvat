"""dpsso 票据端点测试：valid/expired/replayed/forged + 角色映射 + next 白名单。"""
import time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings

from .ticket import sign_ticket

SECRET = "test-secret"
URL = "/api/dp/sso"


def _ticket(payload: dict, secret: str = SECRET) -> str:
    p = {
        "uid": "u1", "name": "Ann Otator", "email": "a@b.c",
        "roles": ["annotator"], "exp": int(time.time()) + 60,
        "nonce": f"n{time.time_ns()}", "next": "/tasks/1/jobs/2",
        **payload,
    }
    return sign_ticket(secret, p)


@override_settings(DP_SSO_SECRET=SECRET)
class SsoTicketTests(TestCase):
    def setUp(self):
        self.c = Client()
        Group.objects.get_or_create(name="worker")

    def test_valid_ticket_logs_in_and_redirects(self):
        r = self.c.get(URL, {"ticket": _ticket({})})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/tasks/1/jobs/2")
        u = get_user_model().objects.get(username="dp-u-u1")
        self.assertTrue(u.groups.filter(name="worker").exists())
        self.assertEqual(u.email, "a@b.c")
        # session 已建立
        self.assertIn("_auth_user_id", self.c.session)

    def test_expired_ticket(self):
        r = self.c.get(URL, {"ticket": _ticket({"exp": int(time.time()) - 10})})
        self.assertEqual(r.status_code, 403)

    def test_forged_ticket(self):
        r = self.c.get(URL, {"ticket": _ticket({}, secret="wrong")})
        self.assertEqual(r.status_code, 403)

    def test_replayed_ticket(self):
        t = _ticket({"nonce": "reused-nonce"})
        self.assertEqual(self.c.get(URL, {"ticket": t}).status_code, 302)
        self.assertEqual(self.c.get(URL, {"ticket": t}).status_code, 403)

    def test_role_mapping_qa_admin(self):
        r = self.c.get(URL, {"ticket": _ticket(
            {"uid": "q1", "roles": ["annotator", "admin"], "nonce": "nq1"})})
        self.assertEqual(r.status_code, 302)
        u = get_user_model().objects.get(username="dp-u-q1")
        self.assertTrue(u.groups.filter(name="admin").exists())

    def test_open_redirect_rejected(self):
        r = self.c.get(URL, {"ticket": _ticket(
            {"nonce": "nr1", "next": "//evil.example/x"})})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "/")

    @override_settings(DP_SSO_SECRET="")
    def test_disabled_without_secret(self):
        r = self.c.get(URL, {"ticket": _ticket({})})
        self.assertEqual(r.status_code, 403)
