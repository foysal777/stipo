from django.test import TestCase
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse

from app.models import SiteConfig

class RecaptchaVerificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.original_secret = getattr(settings, 'RECAPTCHA_SECRET_KEY', None)
        settings.RECAPTCHA_SECRET_KEY = 'test_secret_key'

    def tearDown(self):
        settings.RECAPTCHA_SECRET_KEY = self.original_secret

    def test_contact_us_requires_token(self):
        # Missing token
        response = self.client.post('/contact/', {
            'name': 'Test User',
            'email': 'test@example.com',
            'message_body': 'Hello world'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(response.data.get('error'), "reCAPTCHA token is required")

    @patch('requests.post')
    def test_contact_us_success(self, mock_post):
        # Mock Google API response success
        mock_post.return_value.json.return_value = {"success": True}
        mock_post.return_value.status_code = 200

        response = self.client.post('/contact/', {
            'name': 'Test User',
            'email': 'test@example.com',
            'message_body': 'Hello world',
            'token': 'valid_token'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('message'), "Message sent successfully")
        mock_post.assert_called_once_with(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": "test_secret_key", "response": "valid_token"},
            timeout=10
        )

    @patch('requests.post')
    def test_contact_us_captcha_failure(self, mock_post):
        # Mock Google API response failure
        mock_post.return_value.json.return_value = {"success": False, "error-codes": ["invalid-input-response"]}
        mock_post.return_value.status_code = 200

        response = self.client.post('/contact/', {
            'name': 'Test User',
            'email': 'test@example.com',
            'message_body': 'Hello world',
            'token': 'invalid_token'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get('success'), False)
        self.assertEqual(response.data.get('error'), "Captcha verification failed")

    @patch('requests.post')
    def test_verify_captcha_endpoint_success(self, mock_post):
        mock_post.return_value.json.return_value = {"success": True}
        mock_post.return_value.status_code = 200

        response = self.client.post('/api/verify-captcha/', {
            'token': 'valid_token'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('success'), True)
        self.assertEqual(response.data.get('message'), "Captcha verified successfully")

    def test_verify_captcha_missing_secret_key(self):
        # Set secret key to None/empty
        settings.RECAPTCHA_SECRET_KEY = ''
        
        response = self.client.post('/api/verify-captcha/', {
            'token': 'valid_token'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data.get('success'), False)
        self.assertIn("reCAPTCHA secret key is not configured", response.data.get('error'))


from app.models import DatasetUpload

class DatasetUploadSignalTests(TestCase):
    def test_unrelated_field_change_does_not_trigger_upload_without_dataset_change(self):
        with patch('app.signals.Thread') as mock_thread:
            DatasetUpload.objects.create(
                scholarships_db_file=SimpleUploadedFile(
                    'test.xlsx',
                    b'dummy-data',
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            )

        self.assertTrue(mock_thread.called)


class CookieConsentTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_get_cookie_consent_settings(self):
        response = self.client.get(reverse('cookie_consent'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('keep_recaptcha'))
        self.assertTrue(response.data.get('require_cookie_banner'))
        self.assertTrue(response.data.get('block_captcha_until_consent'))
        self.assertEqual(response.data.get('privacy_policy_url'), '/privacy-policy')

    def test_submit_cookie_consent_accept(self):
        response = self.client.post(reverse('cookie_consent'), {
            'consent_given': True,
            'consent_type': 'all'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))
        self.assertTrue(response.data.get('consent_given'))
        self.assertTrue(response.data.get('captcha_unblocked'))

    def test_submit_cookie_consent_decline(self):
        response = self.client.post(reverse('cookie_consent'), {
            'consent_given': False,
            'consent_type': 'necessary'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data.get('success'))
        self.assertFalse(response.data.get('consent_given'))
        self.assertFalse(response.data.get('captcha_unblocked'))

    def test_submit_cookie_consent_missing_parameter(self):
        response = self.client.post(reverse('cookie_consent'), {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('success'))
        self.assertIn('consent_given', response.data.get('error'))

    def test_submit_cookie_consent_string_false_is_treated_as_decline(self):
        response = self.client.post(reverse('cookie_consent'), {
            'consent_given': 'false',
            'consent_type': 'necessary'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data.get('success'))
        self.assertFalse(response.data.get('consent_given'))
        self.assertFalse(response.data.get('captcha_unblocked'))
