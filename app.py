import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

ROOT = Path(__file__).parent
CONFIG = json.loads((ROOT / 'formats.json').read_text())
app = FastAPI(title='Local converter')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')


def encoders():
    result = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], capture_output=True, text=True, check=True)
    return {line.split()[1] for line in result.stdout.splitlines() if len(line.split()) > 1}


@app.get('/')
def index():
    return FileResponse(ROOT / 'static/index.html')


@app.get('/api/formats')
def formats():
    available = encoders()
    return {**CONFIG, 'formats': [f for f in CONFIG['formats'] if all(e in available for e in f['encoders'])]}


@app.post('/api/convert')
def convert(file: UploadFile = File(...), format: str = Form(...), quality: str = Form('balanced'),
            width: int = Form(0), mute: bool = Form(False)):
    target = next((f for f in CONFIG['formats'] if f['id'] == format), None)
    if target is None or quality not in CONFIG['qualities'] or width not in CONFIG['widths']:
        raise HTTPException(400, 'Invalid export preferences.')
    if not all(e in encoders() for e in target['encoders']):
        raise HTTPException(400, 'This FFmpeg installation lacks the required encoder.')
    folder = Path(tempfile.mkdtemp(prefix='web-tools-'))
    source, output = folder / 'input', folder / ('converted.' + target['extension'])
    try:
        size = 0
        with source.open('wb') as dest:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > CONFIG['max_upload_bytes']:
                    raise HTTPException(413, 'Maximum upload size is 512 MiB.')
                dest.write(chunk)
        args = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y',
                '-protocol_whitelist', 'file,pipe', '-i', str(source), '-map', '0:v:0',
                '-map_metadata', '-1', '-threads', '2']
        if target['kind'] == 'video' and format != 'gif' and not mute:
            args += ['-map', '0:a:0?']
        else:
            args += ['-an']
        filters = []
        if width:
            filters.append(f'scale={width}:-2')
        elif target['kind'] == 'video':
            filters.append('scale=trunc(iw/2)*2:trunc(ih/2)*2')
        if format == 'gif':
            filters.append('fps=12')
        if filters:
            args += ['-vf', ','.join(filters)]
        args += target['args'] + target['quality_args'][quality] + [str(output)]
        result = subprocess.run(args, capture_output=True, timeout=600)
        if result.returncode:
            raise HTTPException(422, 'Conversion failed. Check that the file is a supported video or image.')
        return FileResponse(output, media_type=target['mime'], filename=output.name,
                            background=BackgroundTask(shutil.rmtree, folder))
    except subprocess.TimeoutExpired:
        shutil.rmtree(folder)
        raise HTTPException(408, 'Conversion exceeded the 10-minute limit.')
    except Exception:
        shutil.rmtree(folder)
        raise
