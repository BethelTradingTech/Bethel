import os,shutil,subprocess,threading,time
from pathlib import Path
import requests
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse
from PIL import Image,ImageDraw,ImageFont
API=os.getenv("BETHEL_API_BASE","https://api.betheltradingtechnologies.com").rstrip("/")
SECRET=os.getenv("BROADCAST_WORKER_SECRET","")
ROOT=Path("/tmp/bethel-broadcast"); ROOT.mkdir(parents=True,exist_ok=True)
app=FastAPI(title="Bethel Broadcast Worker")
runtime={"state":"OFF","landscape":False,"vertical":False}
def hdr():return {"X-Bethel-Broadcast-Secret":SECRET}
def get(p):
 r=requests.get(API+p,headers=hdr(),timeout=10);r.raise_for_status();return r.json()
def beat(s,m=None):
 runtime["state"]=s
 try:requests.post(API+"/broadcast/v1/worker/heartbeat",headers=hdr(),json={"state":s,"message":m},timeout=5)
 except Exception:pass
def font(n):
 p="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
 return ImageFont.truetype(p,n) if os.path.exists(p) else ImageFont.load_default()
def money(v,c):
 try:return f"{c} {float(v):,.2f}"
 except:return "—"
def frame(data,size):
 W,H=size;im=Image.new("RGB",size,(8,13,22));d=ImageDraw.Draw(im);c=data.get("currency","USD")
 d.text((30,25),"BETHEL TRADING TECHNOLOGIES",font=font(max(24,W//32)),fill=(16,185,129));d.text((30,75),"LIVE MT5 · READ ONLY",font=font(max(18,W//45)),fill=(240,243,248))
 vals=[("Balance",money(data.get("balance"),c)),("Equity",money(data.get("equity"),c)),("Floating P/L",money(data.get("floating_profit"),c)),("Open Positions",str(data.get("open_position_count",0)))]
 y=140
 for k,v in vals:d.text((30,y),f"{k}: {v}",font=font(max(18,W//50)),fill=(210,216,226));y+=48
 d.text((30,y+15),f"{data.get('terminal_label','Owner / Master')} · {data.get('account_mode','—')} · {data.get('connection_status','OFFLINE')}",font=font(max(16,W//55)),fill=(155,165,180));y+=75
 for p in data.get("positions",[])[:6]:d.text((45,y),f"{p.get('symbol','')} {p.get('direction','')} · Vol {p.get('volume','')} · {money(p.get('profit'),c)}",font=font(max(15,W//60)),fill=(190,198,210));y+=38
 d.text((30,H-45),"MetaTrader EA execution · No trade controls · Past performance does not guarantee future results.",font=font(max(13,W//75)),fill=(115,125,140));return im
class Encoder:
 def __init__(self,n,w,h):self.n=n;self.w=w;self.h=h;self.p=None;self.o=ROOT/n
 def start(self):
  self.stop();self.o.mkdir(parents=True,exist_ok=True);self.p=subprocess.Popen(["ffmpeg","-hide_banner","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{self.w}x{self.h}","-r","2","-i","-","-an","-c:v","libx264","-preset","veryfast","-tune","zerolatency","-pix_fmt","yuv420p","-g","4","-f","hls","-hls_time","2","-hls_list_size","5","-hls_flags","delete_segments+append_list+omit_endlist",str(self.o/"live.m3u8")],stdin=subprocess.PIPE)
 def write(self,im):
  if self.p is None or self.p.poll() is not None:self.start()
  try:self.p.stdin.write(im.tobytes());self.p.stdin.flush()
  except Exception:self.start()
 def stop(self):
  if self.p:
   try:self.p.terminate();self.p.wait(timeout=2)
   except Exception:pass
   self.p=None
  shutil.rmtree(self.o,ignore_errors=True)
L=Encoder("landscape",1280,720);V=Encoder("vertical",720,1280)
def loop():
 if len(SECRET)<64:beat("ERROR","BROADCAST_WORKER_SECRET must be at least 64 characters");return
 while True:
  try:
   cfg=get("/broadcast/v1/worker/config")
   if not cfg.get("enabled"):
    L.stop();V.stop();runtime.update(landscape=False,vertical=False);beat("OFF","Broadcast disabled");time.sleep(3);continue
   src=get("/broadcast/v1/worker/source")
   if not src.get("available"):beat("WAITING","Waiting for owner/master telemetry");time.sleep(3);continue
   if cfg.get("landscape_enabled"):L.write(frame(src,(1280,720)));runtime["landscape"]=True
   else:L.stop();runtime["landscape"]=False
   if cfg.get("vertical_enabled"):V.write(frame(src,(720,1280)));runtime["vertical"]=True
   else:V.stop();runtime["vertical"]=False
   beat("STREAMING","Bethel HLS video outputs active");time.sleep(.5)
  except Exception as e:beat("ERROR",str(e)[:240]);time.sleep(5)
@app.on_event("startup")
def start():threading.Thread(target=loop,daemon=True).start()
@app.get('/health')
def health():return {"status":"healthy",**runtime}
@app.get('/live/{layout}/live.m3u8')
def playlist(layout:str):
 p=ROOT/layout/'live.m3u8'
 if layout not in {'landscape','vertical'} or not p.exists():raise HTTPException(404,"Broadcast is not active")
 return FileResponse(p,media_type='application/vnd.apple.mpegurl',headers={'Cache-Control':'no-store'})
@app.get('/live/{layout}/{segment}')
def segment(layout:str,segment:str):
 if layout not in {'landscape','vertical'} or '/' in segment or '..' in segment:raise HTTPException(404,"Unknown segment")
 p=ROOT/layout/segment
 if not p.exists():raise HTTPException(404,"Segment unavailable")
 return FileResponse(p,media_type='video/mp2t',headers={'Cache-Control':'no-store'})
