"""Checks for the self-contained production encodings in protocol v1.1."""
import json
import struct
from pathlib import Path


def validate_glb(path):
    path=Path(path)
    with path.open('rb') as stream:
        header=stream.read(12)
        if len(header)!=12:raise ValueError('Truncated GLB header')
        magic,version,size=struct.unpack('<4sII',header)
        if magic!=b'glTF' or version!=2 or size!=path.stat().st_size:raise ValueError('Invalid GLB container')
        length,kind=struct.unpack('<I4s',stream.read(8))
        if kind!=b'JSON' or length>size-20:raise ValueError('Invalid GLB JSON chunk')
        document=json.loads(stream.read(length))
        if document.get('asset',{}).get('version')!='2.0':raise ValueError('Unsupported glTF version')
        for item in document.get('buffers',[])+document.get('images',[]):
            uri=item.get('uri','')
            if uri and not uri.startswith('data:'):raise ValueError('GLB must embed its buffers and textures')
    return document


def validate_npy(path, layer, samples, mask=None):
    import numpy as np
    encoding=layer['encoding']
    array=np.load(path,mmap_mode='r',allow_pickle=False)
    if array.dtype.str!=encoding['dtype'] or list(array.shape)!=encoding['shape']:
        raise ValueError('NPY dtype/shape differs from manifest')
    if not array.flags.c_contiguous:raise ValueError('NPY must use C-order layout')
    dynamic=layer['sampling']!='static';vector=layer['kind']=='vector_field'
    axes=('T' if dynamic else '')+('C' if vector else '')+'YX'
    if encoding['axes']!=axes or array.ndim!=len(axes):raise ValueError('NPY axis order mismatch')
    if dynamic and array.shape[0]!=len(samples):raise ValueError('NPY time dimension mismatch')
    if vector and array.shape[1 if dynamic else 0]!=3:raise ValueError('Vector field needs 3 ENU components')
    # Bounded-memory check, including values in frames that are not currently displayed.
    chunks=array if dynamic else [array]
    for chunk in chunks:
        values=chunk if mask is None else chunk[...,mask==0]
        if not np.isfinite(values).all():raise ValueError('NPY contains non-finite values')
