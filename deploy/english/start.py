"""Run the invited English beta with one worker and its persistent archive index."""
import base64
import hmac
import os
import sys
from pathlib import Path

from dotenv import dotenv_values
from starlette.responses import PlainTextResponse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'src'))


class InvitedReaders:
    """Basic authentication is handled by the browser over the host's HTTPS ingress."""

    def __init__(self, app, password):
        if len(password) < 16:
            raise ValueError('Set ENGLISH_BETA_PASSWORD to a private value of at least 16 characters.')
        self.app = app
        self.expected = base64.b64encode(f'reader:{password}'.encode())

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and scope['path'] != '/health':
            header = dict(scope['headers']).get(b'authorization', b'')
            scheme, _, proof = header.partition(b' ')
            if scheme.lower() != b'basic' or not hmac.compare_digest(proof, self.expected):
                response = PlainTextResponse('Enter your beta invitation to continue.', status_code=401,
                    headers={'WWW-Authenticate': 'Basic realm="The Compounder", charset="UTF-8"', 'Cache-Control': 'no-store'})
                return await response(scope, receive, send)
        return await self.app(scope, receive, send)


def main():
    password = os.environ.get('ENGLISH_BETA_PASSWORD', '')
    key = os.environ.get('AI_API_KEY', '').strip()
    if not key or key == 'replace-on-the-server':
        raise RuntimeError('Set AI_API_KEY in the hosting service secrets.')
    if os.environ.get('RAILWAY_ENVIRONMENT_ID') and os.environ.get('RAILWAY_VOLUME_MOUNT_PATH') != str(ROOT / 'database'):
        raise RuntimeError('Attach a persistent Railway volume at /app/database before starting the beta.')
    for name, value in dotenv_values(ROOT / 'english-pilot.env.example').items():
        if name not in {'AI_API_KEY', 'ENGLISH_PILOT_CALL_LIMIT'} and value is not None:
            os.environ.setdefault(name, value)
    os.environ.setdefault('ENGLISH_PILOT_CALL_LIMIT', '150')
    from english_app import app
    from english_pilot import runtime_settings, port_number
    from evidence_retrieval import build_index, ready_index
    import uvicorn

    guarded_app = InvitedReaders(app, password)
    port = port_number(os.environ.get('PORT', '8000'))
    runtime_settings()
    build_index()  # Reuses a compatible persisted index. Two embedding calls on a fresh volume.
    ready_index()
    uvicorn.run(guarded_app, host='0.0.0.0', port=port, workers=1)


if __name__ == '__main__':
    main()
