import subprocess
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from app import app, CONFIG

client = TestClient(app)


@pytest.fixture(scope='module')
def video():
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / 'sample.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=96x64:rate=12',
                        '-f', 'lavfi', '-i', 'sine=frequency=440', '-t', '0.5', '-c:v', 'libx264',
                        '-c:a', 'aac', str(path)], check=True)
        yield path.read_bytes()


@pytest.mark.parametrize('target', CONFIG['formats'], ids=lambda f: f['id'])
def test_conversion(video, target):
    response = client.post('/api/convert', files={'file': ('test.mp4', video)},
                           data={'format': target['id'], 'width': 640})
    assert response.status_code == 200, response.text
    with tempfile.TemporaryDirectory() as folder:
        output = Path(folder) / ('out.' + target['extension'])
        output.write_bytes(response.content)
        result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                                 '-show_entries', 'stream=width', '-of', 'csv=p=0', str(output)],
                                capture_output=True, text=True, check=True)
        assert result.stdout.strip() == '640'


def test_picture_and_invalid_input(video):
    png = client.post('/api/convert', files={'file': ('test.mp4', video)}, data={'format': 'png'})
    response = client.post('/api/convert', files={'file': ('image.png', png.content)}, data={'format': 'webp'})
    assert response.status_code == 200
    assert client.post('/api/convert', files={'file': ('bad', b'not media')}, data={'format': 'mp4'}).status_code == 422
    assert client.post('/api/convert', files={'file': ('test', video)}, data={'format': '../bad'}).status_code == 400
    assert client.get('/').status_code == 200
    assert len(client.get('/api/formats').json()['formats']) == len(CONFIG['formats'])
