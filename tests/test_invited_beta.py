import importlib.util
from pathlib import Path
from unittest import TestCase

from fastapi import FastAPI
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location('hosted_beta', Path(__file__).resolve().parents[1] / 'deploy/english/start.py')
hosted = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hosted)


class InvitedBetaTests(TestCase):
    def test_only_health_is_anonymous_and_wrong_credentials_do_not_reach_paid_path(self):
        app = FastAPI()
        visited = []

        @app.post('/api/english/ask')
        def ask():
            visited.append(True)
            return 'ok'

        @app.get('/health')
        def health():
            return {'status': 'ready'}

        with self.assertRaises(ValueError):
            hosted.InvitedReaders(app, '')
        password = 'only-for-this-unit-test'
        client = TestClient(hosted.InvitedReaders(app, password))
        self.assertEqual(client.get('/health').status_code, 200)
        for path in ('/', '/api/english/sources/example', '/api/english/feedback'):
            self.assertEqual(client.get(path).status_code, 401)
        self.assertEqual(client.post('/api/english/ask', auth=('reader', 'incorrect')).status_code, 401)
        self.assertEqual(visited, [])
        self.assertEqual(client.post('/api/english/ask', auth=('reader', password)).status_code, 200)
        self.assertEqual(visited, [True])
