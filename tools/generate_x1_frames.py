"""Compile the reviewed atlas rectangles; no bitmap conversion or resampling."""
import argparse
import json
from pathlib import Path


def generate(source, output):
    data=json.loads(source.read_text(encoding='utf-8'))
    if data.get('schema')!=1:raise ValueError('Unsupported atlas schema')
    frames=[];sequences=[]
    for sheet in data['sheets']:
        character=sheet['character']
        if character not in (0,1):raise ValueError('Invalid character')
        for name,rectangles in sheet['sequences'].items():
            first=len(frames)
            for rectangle in rectangles:
                if len(rectangle)!=4 or any(type(v) is not int for v in rectangle):raise ValueError('Invalid rectangle')
                x,y,w,h=rectangle
                if min(x,y)<0 or not 0<w<=128 or not 0<h<=128 or x+w>sheet['width'] or y+h>sheet['height']:
                    raise ValueError(('Rectangle exceeds sheet or texture bank',rectangle))
                frames.append((character,x,y,w,h))
            if not rectangles:raise ValueError('Empty animation')
            sequences.append((character,name,first,len(rectangles)))
    text='// Generated from mmx4_x1_frames.json. Original pixels stay in the supplied PNGs.\n'
    text+='static const X1Frame X1Frames[]={\n'
    text+=''.join('    {'+','.join(map(str,f))+'},\n' for f in frames)+'};\n'
    text+='static const X1Sequence X1Sequences[]={\n'
    text+=''.join(f'    {{{c},{json.dumps(n)},{first},{count}}},\n' for c,n,first,count in sequences)+'};\n'
    output.parent.mkdir(parents=True,exist_ok=True)
    if not output.exists() or output.read_text()!=text:output.write_text(text,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();generate(a.source,a.output)
