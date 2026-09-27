"""Local viewer server with explicit project mounts and bounded HTTP range reads."""
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
from .storage import scene_id, within


class ViewerHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, storage, **kwargs):
        self.storage=storage
        super().__init__(*args, **kwargs)

    def do_HEAD(self):self.respond(head=True)
    def do_GET(self):self.respond(head=False)

    def respond(self, head):
        try:
            raw=unquote(urlsplit(self.path).path)
            parts=Path(raw.lstrip('/')).parts
            if '..' in parts or '\\' in raw:raise ValueError('Invalid path')
            if raw=='/api/scenes':
                result=[]
                for path in sorted((self.storage.root/'project').glob('*/project.json')):
                    data=json.loads(path.read_text())
                    result.append({'scene_id':data['scene_id'],'title':data['title'],'views':sorted(p.stem for p in (path.parent/'views').glob('*.json'))})
                return self.json_response(result,head)
            if not parts:
                query=urlsplit(self.path).query
                self.send_response(HTTPStatus.FOUND)
                self.send_header('Location','/src/visualization/viewer/'+('?' + query if query else ''))
                self.send_header('Content-Length','0');self.end_headers();return
            legacy=('src','visualization','legacy')
            if parts[:4]==legacy+('scenes',) and len(parts)>=5 and parts[4]!='index.json':
                old=parts[4]
                aliases={'south_kensington':('south_ken','legacy_web'),'white_city':('white_city','legacy_web'),'region':('windfarm','region'),'windfarm_2m':('windfarm','mac_2m'),'windfarm_crop':('windfarm','crop'),'actuator_lab':('actuator_lab','fullgradient'),'actuator_lab_halfgradient':('actuator_lab','halfgradient')}
                pair=aliases.get(old,('windfarm',old.removeprefix('windfarm_')) if old.startswith('windfarm_') else None)
                if pair is None:self.send_error(HTTPStatus.NOT_FOUND);return
                path=within(self.storage.run(*pair),*parts[5:])
            elif parts[:4]==legacy+('geometry',):
                path=within(self.storage.assets('south_ken','geometry')/'legacy_visualizer',*parts[4:])
            elif parts[:6]==legacy+('agents','demo_rev02','data'):
                path=within(self.storage.run('south_ken','legacy_agents')/'data',*parts[6:])
            elif parts[:2]==('src','visualization') or parts[0] in ('examples','schemas'):
                path=within(self.storage.root,*parts)
            elif parts==('project','index.json'):
                path=self.storage.root/'project/index.json'
                catalog=json.loads(path.read_text())
                for item in catalog['scenes']:
                    views=[]
                    for name in item.get('views',[]):
                        view=json.loads((self.storage.metadata(item['scene_id'])/'views'/f'{name}.json').read_text())
                        if all((self.storage.run(item['scene_id'],rid)/'manifest.json').is_file() for rid in view['runs']):views.append(name)
                    item['views']=views
                catalog['scenes']=[item for item in catalog['scenes'] if item['views']]
                if catalog.get('default') not in {item['scene_id'] for item in catalog['scenes']}:catalog['default']=catalog['scenes'][0]['scene_id'] if catalog['scenes'] else None
                return self.json_response(catalog,head)
            elif parts[0]=='project' and len(parts)>=3:
                scene=scene_id(parts[1]);category=parts[2]
                if scene!=parts[1]:raise ValueError('Use canonical scene ID')
                if category not in ('input','geometry','runs','project.json','configs','views'):raise ValueError('Unknown project category')
                base=self.storage.assets(scene,category) if category in ('input','geometry','runs') else self.storage.metadata(scene)/category
                path=within(base,*parts[3:])
            else:
                self.send_error(HTTPStatus.NOT_FOUND);return
            if path.is_dir():path=path/'index.html'
            if not path.is_file():self.send_error(HTTPStatus.NOT_FOUND);return
            size=path.stat().st_size;start=0;end=size-1;status=HTTPStatus.OK
            requested=self.headers.get('Range')
            if requested:
                match=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
                if not match or not any(match.groups()):return self.bad_range(size)
                if match[1]:
                    start=int(match[1]);end=min(int(match[2]),size-1) if match[2] else size-1
                else:start=max(0,size-int(match[2]))
                if start>=size or start>end:return self.bad_range(size)
                status=HTTPStatus.PARTIAL_CONTENT
            self.send_response(status)
            mime=mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
            self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(max(0,end-start+1)))
            self.send_header('Accept-Ranges','bytes')
            self.send_header('Cache-Control','no-cache')
            if requested:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            self.end_headers()
            if not head:
                with path.open('rb') as stream:
                    stream.seek(start);remaining=end-start+1
                    while remaining>0:
                        chunk=stream.read(min(1<<20,remaining))
                        if not chunk:break
                        self.wfile.write(chunk);remaining-=len(chunk)
        except (ValueError,KeyError):self.send_error(HTTPStatus.BAD_REQUEST)
        except (BrokenPipeError,ConnectionResetError):pass

    def bad_range(self,size):
        self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
        self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers()

    def json_response(self,value,head):
        body=json.dumps(value).encode();self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers()
        if not head:self.wfile.write(body)


def serve(storage,host='127.0.0.1',port=8769):
    handler=partial(ViewerHandler,storage=storage)
    with ThreadingHTTPServer((host,port),handler) as server:
        print(f'Viewer: http://{host}:{server.server_port}/',flush=True)
        print(f'Data: {storage.data_root}',flush=True)
        server.serve_forever()
