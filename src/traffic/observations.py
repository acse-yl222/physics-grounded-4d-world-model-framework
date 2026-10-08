"""Retain local DfT raw hourly counts for both scenes, without claiming OD calibration."""
import csv
from datetime import datetime,timezone
import io
import json
import zipfile
import requests
from common.storage import Storage
from common.export import digest,write
from .sumo_pipeline import configuration,lonlat_to_scene

URL='https://storage.googleapis.com/dft-statistics/road-traffic/downloads/data-gov-uk/dft_traffic_counts_raw_counts.zip'


def fetch(storage):
    folder=storage.scratch('south_ken','traffic','dft_download');folder.mkdir(parents=True,exist_ok=True)
    archive=folder/'raw_counts.zip'
    if not archive.exists():
        with requests.get(URL,stream=True,timeout=60) as response:
            response.raise_for_status()
            temporary=archive.with_suffix('.part')
            with temporary.open('wb') as stream:
                for chunk in response.iter_content(1024*1024):stream.write(chunk)
            temporary.replace(archive)
    configs={s:configuration(storage,s) for s in ('south_ken','white_city')}
    bounds={s:json.loads((storage.metadata(s)/'project.json').read_text())['spatial']['bounds_m'] for s in configs}
    selected={s:[] for s in configs}
    with zipfile.ZipFile(archive) as zipped:
        member=next(n for n in zipped.namelist() if n.endswith('.csv'))
        with zipped.open(member) as file:
            reader=csv.DictReader(io.TextIOWrapper(file,encoding='utf-8-sig'))
            headers=reader.fieldnames
            for row in reader:
                lat=float(row['latitude']);lon=float(row['longitude'])
                if not 51.47<=lat<=51.55 or not -.27<=lon<=-.13:continue
                for scene,cfg in configs.items():
                    x,y=lonlat_to_scene([[lon,lat]],cfg['transform'])[0]
                    b=bounds[scene]
                    if b['min'][0]<=x<=b['max'][0] and b['min'][1]<=y<=b['max'][1]:selected[scene].append(row)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    result={}
    for scene,rows in selected.items():
        out=storage.assets(scene,'input')/'traffic'/('dft_'+stamp);out.mkdir(parents=True,exist_ok=False)
        with (out/'raw_counts.csv').open('w',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=headers);writer.writeheader();writer.writerows(rows)
        years=sorted({int(r['year']) for r in rows})
        result[scene]={'source_url':URL,'source_zip_sha256':digest(archive),'member':member,'retrieved_utc':datetime.now(timezone.utc).isoformat(),
             'license':'Open Government Licence v3.0; DfT road traffic statistics',
             'rows':len(rows),'count_points':len({r['count_point_id'] for r in rows}),'years':years,
             'latest_year':max(years) if years else None,'local_csv_sha256':digest(out/'raw_counts.csv'),
             'scope':'Raw historical hourly counts, spatially filtered in the retained city frame; not AADF, not a full OD matrix. No model calibration has been performed.'}
        write(out/'provenance.json',result[scene]);write(storage.metadata(scene)/'configs/traffic_observations.json',{'input_path':str(out.relative_to(storage.assets(scene,'input'))),**result[scene]})
    return result


if __name__=='__main__':print(json.dumps(fetch(Storage.load()),indent=2))
