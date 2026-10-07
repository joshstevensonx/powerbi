import json, sys, os, glob, urllib.request, hashlib
from jsonschema import Draft7Validator
from referencing import Registry, Resource
CACHE=os.path.join(os.path.dirname(__file__),'..','schemas','cache'); os.makedirs(CACHE,exist_ok=True)
PFX='https://developer.microsoft.com/json-schemas/'
RAW='https://raw.githubusercontent.com/microsoft/json-schemas/main/'
def fetch(uri):
    fn=os.path.join(CACHE,hashlib.md5(uri.encode()).hexdigest()+'.json')
    if not os.path.exists(fn):
        u=uri.replace(PFX,RAW)
        for a,b in [('visualContainer/2.13.0','visualContainer/2.12.0'),('report/3.4.0','report/3.3.0')]: pass
        try: data=urllib.request.urlopen(u).read()
        except Exception:
            u=u.replace('visualContainer/2.13.0','visualContainer/2.12.0')
            data=urllib.request.urlopen(u).read()
        open(fn,'wb').write(data)
    return Resource.from_contents(json.load(open(fn)))
reg=Registry(retrieve=fetch)
errs=0
for f in sys.argv[1:]:
    d=json.load(open(f))
    s=d.get('$schema')
    if not s: continue
    sch=fetch(s).contents
    v=Draft7Validator(sch,registry=reg)
    es=[e for e in v.iter_errors(d) if list(e.absolute_path)!=['$schema']]
    for e in es[:5]:
        errs+=1; print(f, '/'.join(map(str,e.absolute_path)), e.message[:300])
print('errors',errs)
