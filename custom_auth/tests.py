from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.views import TokenRefreshView

from . import views
from .models import User


class JWTTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def perform_request(self, method, view, url, data={}, factory=None):
        factory = factory or self.factory
        request = getattr(factory, method)(url, data, format='json')
        response = view.as_view()(request)
        response.render()
        return response

    def get(self, *args, **kwargs):
        return self.perform_request('get', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.perform_request('post', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.perform_request('put', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.perform_request('delete', *args, **kwargs)


class AuthenticationTest(JWTTestCase):
    def setUp(self):
        super().setUp()
        self.email = 'test@test.com'
        self.password = 'password'

        self.user = User(email=self.email)
        self.user.set_password(self.password)
        self.user.save()

    def test_correct_login(self):
        response = self.post(views.Login, '/user/login/', {'email': self.email, 'password': self.password})
        self.assertEquals(response.status_code, 200, msg=response.content)

    def test_incorrect_login(self):
        response = self.post(views.Login, '/user/login/', {'email': self.email, 'password': 'wrong'})
        self.assertEquals(response.status_code, 400, msg=response.content)

    def test_correct_JWT_refresh(self):
        response = self.post(views.Login, '/user/login/', {'email': self.email, 'password': self.password})
        access_token = response.data['access']
        refresh_token = response.data['refresh']

        response = self.post(TokenRefreshView, '/user/refresh/', {'refresh': refresh_token})
        self.assertEquals(response.status_code, 200, msg=response.content)
        self.assertNotEqual(response.data['access'], access_token)

    def test_incorrect_JWT_refresh(self):
        response = self.post(views.Login, '/user/login/', {'email': self.email, 'password': self.password})
        access_token = response.data['access']
        refresh_token = response.data['refresh']

        response = self.post(TokenRefreshView, '/user/refresh/', {'refresh': f'{refresh_token}a'})
        self.assertEquals(response.status_code, 401, msg=response.content)