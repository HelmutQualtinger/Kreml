import json,sys,math
src,extra,out=sys.argv[1:4]
LAT0,LON0=55.7506,37.6175
def xy(p): return ((p['lon']-LON0)*62650,-(p['lat']-LAT0)*111200)
XMIN,XMAX,ZMIN,ZMAX=-470,540,-640,430
def rings_of(e,role=None):
    if e['type']=='way':
        g=e.get('geometry') or []
        return [[xy(p) for p in g]] if role in(None,'outer') and len(g)>3 else []
    segs=[[ (p['lat'],p['lon']) for p in m['geometry']] for m in e['members'] if m['type']=='way' and 'geometry' in m and (m['role'] or 'outer')==role]
    rings=[]
    while segs:
        r=segs.pop(0)
        while r[0]!=r[-1]:
            for i,s in enumerate(segs):
                if s[0]==r[-1]: r+=s[1:]; segs.pop(i); break
                if s[-1]==r[-1]: r+=s[-2::-1]; segs.pop(i); break
            else: break
        if len(r)>3: rings.append([xy({'lat':a,'lon':b}) for a,b in r])
    return rings
def dp(pts,eps):
    if len(pts)<3: return pts
    (ax,ay),(bx,by)=pts[0],pts[-1]; L=math.hypot(bx-ax,by-ay) or 1e-9
    dm,im=0,0
    for i in range(1,len(pts)-1):
        px,py=pts[i]; dd=abs((bx-ax)*(ay-py)-(ax-px)*(by-ay))/L
        if dd>dm: dm,im=dd,i
    if dm<=eps: return [pts[0],pts[-1]]
    return dp(pts[:im+1],eps)[:-1]+dp(pts[im:],eps)
def simp(r,eps=0.35):
    if r[0]==r[-1]: r=r[:-1]
    if len(r)<5: return r
    # split at farthest point from r[0] to keep closed shape
    k=max(range(len(r)),key=lambda i:(r[i][0]-r[0][0])**2+(r[i][1]-r[0][1])**2)
    a=dp(r[:k+1],eps); b=dp(r[k:]+[r[0]],eps)
    return a[:-1]+b[:-1]
def flat(r): return [round(v,1) for p in r for v in p]
def area(r): return abs(sum(r[i][0]*r[(i+1)%len(r)][1]-r[(i+1)%len(r)][0]*r[i][1] for i in range(len(r))))/2
def cen(r):
    xs=[p[0] for p in r]; zs=[p[1] for p in r]; return ((min(xs)+max(xs))/2,(min(zs)+max(zs))/2)
def inside(pt,r):
    x,y=pt; c=False
    for i in range(len(r)):
        (x1,y1),(x2,y2)=r[i],r[i-1]
        if (y1>y)!=(y2>y) and x<(x2-x1)*(y-y1)/(y2-y1)+x1: c=not c
    return c
def inreg(r):
    x,z=cen(r); return XMIN<x<XMAX and ZMIN<z<ZMAX
def rect(pts):
    best=None
    for deg in range(-45,45):
        a=math.radians(deg); c,s=math.cos(a),math.sin(a)
        us=[p[0]*c+p[1]*s for p in pts]; vs=[-p[0]*s+p[1]*c for p in pts]
        w,dd=max(us)-min(us),max(vs)-min(vs)
        if best is None or w*dd<best[0]:
            u0,v0=(max(us)+min(us))/2,(max(vs)+min(vs))/2
            best=(w*dd,[round(u0*c-v0*s,1),round(u0*s+v0*c,1),round(w,1),round(dd,1),round(a,3)])
    return best[1]
def fnum(s):
    try: return float(str(s).replace('m','').strip())
    except: return None
d=json.load(open(src)); x=json.load(open(extra))
B=[];report=[]
for e in d['elements']:
    t=e.get('tags',{})
    if 'building' not in t or t['building']=='no': continue
    outs=rings_of(e,'outer'); inns=rings_of(e,'inner') if e['type']=='relation' else []
    outs=[r for r in outs if inreg(r)]
    if not outs: continue
    h=fnum(t.get('height')); lv=fnum(t.get('building:levels'))
    allp=[p for r in outs for p in r]
    name=t.get('name:de') or t.get('name') or ''
    for k,r in enumerate(sorted(outs,key=area,reverse=True)):
        s=simp(r)
        if len(s)<3 or area(s)<4: continue
        holes=[flat(simp(q)) for q in inns if inside(q[0],r) and area(q)>6]
        B.append({'id':e['id'],'n':name,'k':t['building'],'h':h or 0,'lv':lv or 0,'c':t.get('building:colour',''),'rc':t.get('roof:colour',''),'rs':t.get('roof:shape',''),'o':flat(s),'i':holes,'r':rect(r),'p':k})
    if name: report.append((name,e['id'],len(outs),len(inns),rect(allp),h))
# --- Grosser Kremlpalast: Facettenpalast und Gewandniederlegungskirche aus dem Gesamtumriss loesen
B=[b for b in B if b['id'] not in (6233742,16265033)]
def cut(main,a,b,tag,name):
    o=main['o']; pts=[(o[i],o[i+1]) for i in range(0,len(o),2)]
    near=lambda q:min(range(len(pts)),key=lambda i:(pts[i][0]-q[0])**2+(pts[i][1]-q[1])**2)
    i,j=near(a),near(b); assert i<j,(i,j)
    part=pts[i:j+1]
    main['o']=flat(pts[:i+1]+pts[j:])
    B.append({'id':main['id'],'n':name,'k':tag,'h':0,'lv':0,'c':'white','rc':'','rs':'','o':flat(part),'i':[],'r':rect(part),'p':0,'t':tag})
g=[b for b in B if b['id']==225033 and b['p']==0][0]
cut(g,(-61.1,33.3),(-63.9,-0.4),'facets','Facettenpalast')
cut(g,(-62.3,-12.4),(-62.8,-26.9),'depo','Gewandniederlegungskirche')
def polys(pred,minarea=8,eps=0.5):
    res=[]
    for e in x['elements']+d['elements']:
        t=e.get('tags',{})
        if not pred(t): continue
        for r in rings_of(e,'outer'):
            if inreg(r) and area(r)>minarea:
                inn=[flat(simp(q,eps)) for q in (rings_of(e,'inner') if e['type']=='relation' else []) if inside(q[0],r) and area(q)>20]
                res.append({'n':t.get('name:de') or t.get('name') or '','o':flat(simp(r,eps)),'i':inn})
    return res
GR=polys(lambda t:t.get('landuse')=='grass' or t.get('natural')=='scrub')
WD=polys(lambda t:t.get('natural')=='wood')
SQ=polys(lambda t:(t.get('highway')=='pedestrian' or t.get('place')=='square') and t.get('name'),eps=0.8)
BR=polys(lambda t:t.get('man_made')=='bridge')
# water: clip to region
def clip(r,x0,x1,z0,z1):
    def cl(r,ins,inter):
        o=[]
        for i in range(len(r)):
            a,b=r[i-1],r[i]
            if ins(b):
                if not ins(a): o.append(inter(a,b))
                o.append(b)
            elif ins(a): o.append(inter(a,b))
        return o
    def ix(v): return lambda a,b:(v,a[1]+(b[1]-a[1])*(v-a[0])/(b[0]-a[0]))
    def iz(v): return lambda a,b:(a[0]+(b[0]-a[0])*(v-a[1])/(b[1]-a[1]),v)
    for ins,inter in((lambda p:p[0]>=x0,ix(x0)),(lambda p:p[0]<=x1,ix(x1)),(lambda p:p[1]>=z0,iz(z0)),(lambda p:p[1]<=z1,iz(z1))):
        if r: r=cl(r,ins,inter)
    return r
WA=[]
for e in d['elements']:
    t=e.get('tags',{})
    if t.get('natural')!='water': continue
    for r in rings_of(e,'outer'):
        if r[0]==r[-1]: r=r[:-1]
        c=clip(r,-1500,1500,-900,1300)
        if len(c)>2 and area(c)>40: WA.append({'o':flat(simp(c+[c[0]],0.8))})
gates=[{'n':e['tags'].get('name',''),'p':[round(v,1) for v in xy(e)]} for e in d['elements'] if e['type']=='node' and e.get('tags',{}).get('historic')=='city_gate']
data={'B':B,'GR':GR,'WD':WD,'SQ':SQ,'BR':BR,'WA':WA,'gates':gates}
js='window.KREML='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n'
open(out,'w').write('// Grundrisse: © OpenStreetMap-Mitwirkende (ODbL). Lokale Meterkoordinaten, Ursprung Kathedralenplatz.\n'+js)
print(len(js),'bytes; buildings',len(B),'grass',len(GR),'wood',len(WD),'sq',[s['n'] for s in SQ],'water',len(WA),[len(w['o'])//2 for w in WA][:8])
for r in sorted(report,key=lambda r:r[4][0]**2+r[4][1]**2): print(r)
for b in B:
    if b['id'] in(225033,1359248,1359278,3031379) : print('RING',b['id'],b['p'],len(b['o'])//2,'holes',len(b['i']),b['r'])
