"""The one-command stack must not inherit stale deployment/local port addresses."""
import os
import runpy
from pathlib import Path


def test_dev_api_origin_matches_the_web_port_without_changing_parent_environment(monkeypatch):
    monkeypatch.setenv('WEB_URL', 'http://localhost:5174')
    dev = runpy.run_path(str(Path(__file__).resolve().parents[3] / 'dev.py'))
    env = dev['server_env']('api')
    assert env['WEB_URL'] == 'http://localhost:5173'
    assert os.environ['WEB_URL'] == 'http://localhost:5174'


def test_dev_web_and_extension_use_the_same_local_api(monkeypatch):
    monkeypatch.setenv('VITE_API_URL', 'https://api.example.test')
    monkeypatch.setenv('VITE_WEB_URL', 'https://example.test')
    dev = runpy.run_path(str(Path(__file__).resolve().parents[3] / 'dev.py'))
    for name in ('web', 'ext'):
        env = dev['server_env'](name)
        assert env['VITE_API_URL'] == 'http://localhost:8010'
        assert env['VITE_WEB_URL'] == 'http://localhost:5173'
    assert os.environ['VITE_API_URL'] == 'https://api.example.test'
