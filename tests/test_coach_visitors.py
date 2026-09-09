"""Different browsers must never share saved learning progress or company notes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database import Base, get_db


def test_visitor_progress_and_records_are_isolated():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    def database():
        with sessions() as db:
            yield db
    server.app.dependency_overrides[get_db] = database
    try:
        alice, bob = TestClient(server.app), TestClient(server.app)
        response = alice.post('/api/coach/state', json={'onboarding_completed': True})
        assert response.status_code == 200
        assert 'HttpOnly' in response.headers['set-cookie']
        assert alice.get('/api/coach/state').json()['onboarding_completed'] is True
        assert bob.get('/api/coach/state').json()['onboarding_completed'] is False
        record = {'company_id': 'coke', 'company_name': 'Coca-Cola', 'module_id': '1', 'module_summary': 'private notes'}
        assert alice.post('/api/coach/record', json=record).status_code == 200
        assert alice.get('/api/coach/companies').json()[0]['company_id'] == 'coke'
        assert bob.get('/api/coach/companies').json() == []
        assert bob.get('/api/coach/company/coke').status_code == 404
        assert 'private notes' in alice.get('/api/coach/company/coke').text
        record['module_summary'] = 'other notes'
        bob.post('/api/coach/record', json=record)
        assert 'other notes' not in alice.get('/api/coach/company/coke').text
        assert 'private notes' not in bob.get('/api/coach/company/coke').text
    finally:
        server.app.dependency_overrides.clear()
        engine.dispose()
