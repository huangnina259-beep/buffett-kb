"""Create the upload directory for the invited English service, using committed files only."""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ('ai_gateway', 'ai_settings', 'embedding_gateway', 'english_app', 'english_qa',
           'english_feedback', 'evidence_retrieval', 'evidence_runtime', 'lexical_search',
           'source_contexts', 'source_reading_notes', 'vector_store')
FILES = ('data/source_contexts.json', 'data/source_reading_notes.json', 'frontend/english.html',
         'english-pilot.env.example', 'scripts/english_pilot.py', 'scripts/review_english_pilot.py',
         'deploy/english/start.py', 'deploy/english/requirements.txt', *[f'src/{name}.py' for name in RUNTIME])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, help='New directory outside the repository')
    args = parser.parse_args()
    dest = args.destination.resolve()
    if dest == ROOT or ROOT in dest.parents:
        parser.error('Use a destination outside the checkout.')
    if dest.exists():
        parser.error('Choose a new directory to avoid overwriting files.')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    files = {name: name for name in FILES}
    files.update({'Dockerfile': 'deploy/english/Dockerfile', 'railway.toml': 'deploy/english/railway.toml'})
    content = {name: subprocess.check_output(['git', 'show', f'{commit}:{src}'], cwd=ROOT) for name, src in files.items()}
    dest.mkdir(parents=True)
    for name, data in content.items():
        path = dest / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(f'{dest} contains {len(content)} files from {commit}.')


if __name__ == '__main__':
    main()
