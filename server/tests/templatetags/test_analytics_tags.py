import datetime
import unittest

from django.contrib.auth.models import AnonymousUser, User
from django.test import SimpleTestCase, override_settings

from server.templatetags.analytics_tags import (
    INTERCOM_LAYOUT_SETTINGS,
    intercom_settings,
)


class AnalyticsTagTests(SimpleTestCase):
    @override_settings(
        INTERCOM_APP_ID=None,
        INTERCOM_IDENTITY_VERIFICATION_SECRET=None,
    )
    def test_no_tags(self):
        self.assertIsNone(intercom_settings({"user": AnonymousUser()}))

    @override_settings(
        INTERCOM_APP_ID="app123",
        INTERCOM_IDENTITY_VERIFICATION_SECRET=None,
    )
    def test_intercom_app_no_user_no_verification(self):
        self.assertEqual(
            intercom_settings({"user": AnonymousUser()}),
            dict(app_id="app123", **INTERCOM_LAYOUT_SETTINGS),
        )

    @override_settings(
        INTERCOM_APP_ID="app123",
        INTERCOM_IDENTITY_VERIFICATION_SECRET="verify",
    )
    def test_intercom_app_no_user_with_verification(self):
        self.assertEqual(
            intercom_settings({"user": AnonymousUser()}),
            dict(app_id="app123", **INTERCOM_LAYOUT_SETTINGS),
        )

    @override_settings(
        INTERCOM_APP_ID="app123",
        INTERCOM_IDENTITY_VERIFICATION_SECRET=None,
    )
    def test_intercom_app_with_user_no_verification(self):
        self.assertEqual(
            intercom_settings(
                {
                    "user": User(
                        id=123,
                        first_name="Adam",
                        last_name="Hooper",
                        email="adam@adamhooper.com",
                        date_joined=datetime.datetime(2021, 6, 8, 17, 55, 20),
                    )
                }
            ),
            dict(
                app_id="app123",
                user_id="123",
                name="Adam Hooper",
                email="adam@adamhooper.com",
                created_at=1623174920,
                **INTERCOM_LAYOUT_SETTINGS,
            ),
        )

    @override_settings(
        INTERCOM_APP_ID="app123",
        INTERCOM_IDENTITY_VERIFICATION_SECRET="verify",
    )
    def test_intercom_app_with_user_with_verification(self):
        self.assertEqual(
            intercom_settings(
                {
                    "user": User(
                        id=123,
                        first_name="Adam",
                        last_name="Hooper",
                        email="adam@adamhooper.com",
                        date_joined=datetime.datetime(2021, 6, 8, 17, 55, 20),
                    )
                }
            ),
            dict(
                app_id="app123",
                user_id="123",
                name="Adam Hooper",
                email="adam@adamhooper.com",
                created_at=1623174920,
                user_hash="c0aabdbe284af89bc4f0da53f499d84137ddfc0091deb486355c8db544411cce",
                **INTERCOM_LAYOUT_SETTINGS,
            ),
        )
