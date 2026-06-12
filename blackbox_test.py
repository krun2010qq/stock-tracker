"""Black-box API tests against local or remote stock-tracker instance."""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

BASE_URL = os.environ.get("TEST_BASE_URL", "http://49.51.195.205").rstrip("/")
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@stocktracker.com")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "Admin123456")


@dataclass
class Case:
    name: str
    ok: bool
    detail: str = ""


class BlackBoxTester:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=30.0, follow_redirects=True)
        self.results: list[Case] = []
        self.user_token: str | None = None
        self.user_id: str | None = None
        self.admin_token: str | None = None
        self.test_email = f"bb_{int(time.time())}_{uuid.uuid4().hex[:6]}@example.com"
        self.test_password = "BlackBox123"

    def record(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append(Case(name=name, ok=ok, detail=detail))
        status = "PASS" if ok else "FAIL"
        line = f"[{status}] {name}"
        if detail:
            line += f" -> {detail}"
        print(line)

    def get_json(self, path: str, token: str | None = None, expect: int = 200) -> tuple[int, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = self.client.get(path, headers=headers)
        data = response.json() if response.content else None
        return response.status_code, data

    def post_json(self, path: str, payload: dict, token: str | None = None, expect: int = 200) -> tuple[int, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = self.client.post(path, json=payload, headers=headers)
        data = response.json() if response.content else None
        return response.status_code, data

    def put_json(self, path: str, payload: dict, token: str | None = None) -> tuple[int, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = self.client.put(path, json=payload, headers=headers)
        data = response.json() if response.content else None
        return response.status_code, data

    def patch_json(self, path: str, payload: dict, token: str | None = None) -> tuple[int, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = self.client.patch(path, json=payload, headers=headers)
        data = response.json() if response.content else None
        return response.status_code, data

    def delete(self, path: str, token: str | None = None) -> tuple[int, Any]:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = self.client.delete(path, headers=headers)
        data = response.json() if response.content else None
        return response.status_code, data

    def test_health(self) -> None:
        code, data = self.get_json("/api/health")
        self.record("health endpoint", code == 200 and data == {"status": "ok"}, f"code={code} data={data}")

    def test_pages(self) -> None:
        for path in ["/", "/login.html", "/register.html", "/admin.html"]:
            response = self.client.get(path)
            ok = response.status_code == 200 and "<html" in response.text.lower()
            self.record(f"page {path}", ok, f"code={response.status_code}")

        index = self.client.get("/").text
        self.record("index uses dashboard.js", "dashboard.js" in index)
        self.record("index no requireAuth in html", "requireAuth" not in index)

        app_js = self.client.get("/static/app.js").text
        self.record("legacy app.js shim present", "dashboard.js" in app_js)

        dashboard_js = self.client.get("/static/dashboard.js").text
        self.record("dashboard.js has no requireAuth", "requireAuth" not in dashboard_js)

    def test_guest_quotes(self) -> None:
        code, data = self.get_json("/api/quotes")
        ok = (
            code == 200
            and data.get("is_authenticated") is False
            and len(data.get("quotes", [])) >= 1
            and data.get("tracked_symbols") == ["GOOGL", "NVDA", "AVGO"]
        )
        self.record("guest quotes", ok, f"code={code} symbols={data.get('tracked_symbols') if data else None}")

    def test_symbols(self) -> None:
        code, data = self.get_json("/api/symbols")
        ok = code == 200 and len(data.get("featured", [])) >= 3 and len(data.get("markets", [])) == 3
        self.record("symbols catalog", ok, f"code={code} featured={len(data.get('featured', [])) if data else 0}")

    def test_symbol_search(self) -> None:
        code, data = self.get_json("/api/symbols/search?q=nvda&market=nasdaq")
        results = data.get("results", []) if data else []
        ok = code == 200 and any(item.get("symbol") == "NVDA" for item in results)
        self.record("search nasdaq symbol", ok, f"code={code} hits={len(results)}")

        code2, data2 = self.get_json("/api/symbols/search?q=600519&market=ashare")
        results2 = data2.get("results", []) if data2 else []
        ok2 = code2 == 200 and any("600519" in (item.get("symbol") or "") for item in results2)
        self.record("search ashare symbol", ok2, f"code={code2} hits={len(results2)}")

    def test_register(self) -> None:
        code, data = self.post_json(
            "/api/auth/register",
            {
                "email": self.test_email,
                "password": self.test_password,
                "display_name": "BlackBox User",
            },
        )
        ok = code == 200 and data and data.get("access_token") and data["user"]["email"] == self.test_email
        if ok:
            self.user_token = data["access_token"]
            self.user_id = data["user"]["id"]
        self.record("register new user", ok, f"code={code} detail={data}")

        code2, data2 = self.post_json(
            "/api/auth/register",
            {"email": self.test_email, "password": self.test_password, "display_name": "Dup"},
        )
        self.record("register duplicate rejected", code2 == 400, f"code={code2} detail={data2}")

    def test_login(self) -> None:
        code, data = self.post_json(
            "/api/auth/login",
            {"email": self.test_email, "password": self.test_password},
        )
        ok = code == 200 and data and data.get("access_token")
        if ok:
            self.user_token = data["access_token"]
        self.record("login valid user", ok, f"code={code}")

        code2, data2 = self.post_json(
            "/api/auth/login",
            {"email": self.test_email, "password": "wrong-password"},
        )
        self.record("login wrong password rejected", code2 == 401, f"code={code2}")

    def test_me(self) -> None:
        code, data = self.get_json("/api/auth/me", token=self.user_token)
        ok = code == 200 and data["user"]["email"] == self.test_email and data["user"]["is_admin"] is False
        self.record("auth me", ok, f"code={code}")

        code2, _ = self.get_json("/api/auth/me")
        self.record("auth me without token rejected", code2 == 401, f"code={code2}")

    def test_preferences(self) -> None:
        code, data = self.get_json("/api/preferences", token=self.user_token)
        ok = code == 200 and "preferences" in data and "available_symbols" in data
        self.record("get preferences", ok, f"code={code}")

        code2, data2 = self.put_json(
            "/api/preferences",
            {"favorite_symbols": ["AAPL", "MSFT", "600519.SS"], "news_per_symbol": 6},
            token=self.user_token,
        )
        ok2 = code2 == 200 and data2["preferences"]["favorite_symbols"] == ["AAPL", "MSFT", "600519.SS"]
        self.record("save preferences with ashare", ok2, f"code={code2} prefs={data2}")

        code3, data3 = self.get_json("/api/quotes", token=self.user_token)
        ok3 = (
            code3 == 200
            and data3.get("is_authenticated") is True
            and data3.get("tracked_symbols") == ["AAPL", "MSFT", "600519.SS"]
            and data3.get("news_per_symbol") == 6
        )
        self.record("authenticated quotes use preferences", ok3, f"symbols={data3.get('tracked_symbols') if data3 else None}")

        code4, data4 = self.put_json(
            "/api/preferences",
            {"favorite_symbols": [], "news_per_symbol": 4},
            token=self.user_token,
        )
        self.record("preferences validation rejects empty symbols", code4 == 422, f"code={code4}")

        code5, _ = self.get_json("/api/preferences")
        self.record("preferences without token rejected", code5 == 401, f"code={code5}")

        code6, _ = self.put_json(
            "/api/preferences",
            {"favorite_symbols": ["FAKE1", "FAKE2"], "news_per_symbol": 4},
            token=self.user_token,
        )
        self.record("preferences reject invalid symbols", code6 in (400, 422), f"code={code6}")

        code7, _ = self.put_json(
            "/api/preferences",
            {
                "favorite_symbols": [
                    "AAPL", "MSFT", "NVDA", "GOOGL", "AMD", "META",
                    "TSLA", "AMZN", "NFLX", "AVGO", "600519.SS", "000001.SZ", "300750.SZ",
                ],
                "news_per_symbol": 4,
            },
            token=self.user_token,
        )
        self.record("preferences reject too many symbols", code7 == 422, f"code={code7}")

    def test_admin_auth(self) -> None:
        code, data = self.post_json(
            "/api/auth/login",
            {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        ok = code == 200 and data and data.get("access_token") and data["user"]["is_admin"] is True
        if ok:
            self.admin_token = data["access_token"]
        self.record("admin login", ok, f"code={code} detail={data}")

        code2, _ = self.get_json("/api/admin/stats", token=self.user_token)
        self.record("admin api blocked for normal user", code2 == 403, f"code={code2}")

    def test_admin_panel(self) -> None:
        code, data = self.get_json("/api/admin/stats", token=self.admin_token)
        ok = code == 200 and "total_users" in data.get("stats", {})
        self.record("admin stats", ok, f"code={code} stats={data}")

        code2, data2 = self.get_json("/api/admin/users", token=self.admin_token)
        users = data2.get("users", []) if data2 else []
        found = any(u.get("email") == self.test_email for u in users)
        self.record("admin users list contains test user", code2 == 200 and found, f"code={code2}")

        if self.user_id:
            code3, data3 = self.patch_json(
                f"/api/admin/users/{self.user_id}",
                {"display_name": "BB Renamed"},
                token=self.admin_token,
            )
            ok3 = code3 == 200 and data3["user"]["display_name"] == "BB Renamed"
            self.record("admin update user", ok3, f"code={code3}")

            code4, _ = self.patch_json(
                f"/api/admin/users/{self.user_id}",
                {"is_active": False},
                token=self.admin_token,
            )
            self.record("admin disable user", code4 == 200, f"code={code4}")

            code5, _ = self.post_json(
                "/api/auth/login",
                {"email": self.test_email, "password": self.test_password},
            )
            self.record("disabled user cannot login", code5 == 403, f"code={code5}")

            code5b, data5b = self.get_json("/api/quotes", token=self.user_token)
            guest_mode = (
                code5b == 200
                and data5b.get("is_authenticated") is False
                and data5b.get("tracked_symbols") == ["GOOGL", "NVDA", "AVGO"]
            )
            self.record("disabled user token treated as guest", guest_mode, f"data={data5b}")

            code6, _ = self.patch_json(
                f"/api/admin/users/{self.user_id}",
                {"is_active": True},
                token=self.admin_token,
            )
            self.record("admin re-enable user", code6 == 200, f"code={code6}")

            code7, _ = self.delete(f"/api/admin/users/{self.user_id}", token=self.admin_token)
            self.record("admin delete user", code7 == 200, f"code={code7}")

            code8, _ = self.get_json("/api/auth/me", token=self.user_token)
            self.record("deleted user token rejected", code8 == 401, f"code={code8}")
            self.user_id = None

    def test_news_and_polymarket(self) -> None:
        code, data = self.get_json("/api/news")
        ok = code == 200 and isinstance(data.get("news_by_symbol"), dict)
        self.record("guest news", ok, f"code={code}")

        code2, data2 = self.get_json("/api/polymarket")
        ok2 = code2 == 200 and isinstance(data2.get("markets"), dict)
        self.record("guest polymarket", ok2, f"code={code2}")

    def run(self) -> int:
        print(f"Testing {self.base_url}\n")
        self.test_health()
        self.test_pages()
        self.test_guest_quotes()
        self.test_symbols()
        self.test_symbol_search()
        self.test_news_and_polymarket()
        self.test_register()
        self.test_login()
        self.test_me()
        self.test_preferences()
        self.test_admin_auth()
        self.test_admin_panel()

        failed = [r for r in self.results if not r.ok]
        print(f"\nSummary: {len(self.results) - len(failed)}/{len(self.results)} passed")
        if failed:
            print("Failures:")
            for item in failed:
                print(f"  - {item.name}: {item.detail}")
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(BlackBoxTester(BASE_URL).run())
