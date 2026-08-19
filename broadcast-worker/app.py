import os,shutil,subprocess,threading,time,uuid,json,hmac
from pathlib import Path
import requests
from fastapi import FastAPI,HTTPException,Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image,ImageDraw,ImageFont
API=os.getenv("BETHEL_API_BASE","https://api.betheltradingtechnologies.com").rstrip("/")
SECRET=os.getenv("BROADCAST_WORKER_SECRET","")
ROOT=Path("/tmp/bethel-broadcast"); ROOT.mkdir(parents=True,exist_ok=True)
MEDIA_ROOT=Path(os.getenv("MEDIA_ROOT","/var/data/bethel-media")); MEDIA_ROOT.mkdir(parents=True,exist_ok=True)
MEDIA_SHARE_TTL_SECONDS=max(3600,min(30*24*3600,int(os.getenv("MEDIA_SHARE_TTL_HOURS","168"))*3600))
SOCIAL_URLS={
 "youtube":os.getenv("YOUTUBE_RTMPS_URL","").strip(),
 "facebook":os.getenv("FACEBOOK_RTMPS_URL","").strip(),
 "instagram":os.getenv("INSTAGRAM_RTMPS_URL","").strip(),
 "tiktok":os.getenv("TIKTOK_RTMPS_URL","").strip(),
}
app=FastAPI(title="Bethel Broadcast Worker")
app.add_middleware(
 CORSMiddleware,
 allow_origins=[
  "https://betheltradingtechnologies.com",
  "https://www.betheltradingtechnologies.com",
 ],
 allow_credentials=False,
 allow_methods=["GET","OPTIONS"],
 allow_headers=["*"],
 expose_headers=["Content-Length","Content-Range"],
)
runtime={"state":"OFF","landscape":False,"vertical":False}
def hdr():return {"X-Bethel-Broadcast-Secret":SECRET}
def media_auth(v):
 if len(SECRET)<64 or not v or not hmac.compare_digest(v,SECRET):raise HTTPException(401,"Invalid media worker authentication")
 return True
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
def safe_number(v):
 try:return float(v or 0)
 except:return 0.0
def trade_text(p,c):
 symbol=str(p.get("symbol","")).upper()[:18]
 direction=str(p.get("direction","")).upper()[:4]
 volume=p.get("volume","")
 return f"{symbol}  {direction}  Vol {volume}  P/L {money(p.get('profit'),c)}"
def frame(data,size):
 W,H=size;im=Image.new("RGB",size,(8,13,22));d=ImageDraw.Draw(im);c=data.get("currency","USD")
 compact=H<=800
 title_font=font(max(22,W//34));sub_font=font(max(16,W//50));metric_font=font(max(16,W//58));row_font=font(max(13,W//72));head_font=font(max(15,W//62))
 d.text((30,20 if compact else 25),"BETHEL TRADING TECHNOLOGIES",font=title_font,fill=(16,185,129))
 d.text((30,58 if compact else 75),"LIVE MT5 · READ ONLY",font=sub_font,fill=(240,243,248))
 vals=[("Balance",money(data.get("balance"),c)),("Equity",money(data.get("equity"),c)),("Floating P/L",money(data.get("floating_profit"),c)),("Open Positions",str(data.get("open_position_count",0)))]
 if compact:
  left_x,right_x=30,max(360,W//2+20)
  for i,(k,v) in enumerate(vals):
   x=left_x if i%2==0 else right_x;y=102+(i//2)*34
   d.text((x,y),f"{k}: {v}",font=metric_font,fill=(210,216,226))
  y=178
  d.text((30,150),f"{data.get('terminal_label','Owner / Master')} · {data.get('account_mode','—')} · {data.get('connection_status','OFFLINE')}",font=font(max(14,W//78)),fill=(155,165,180))
  row_step=27;section_gap=12
 else:
  y=140
  for k,v in vals:d.text((30,y),f"{k}: {v}",font=metric_font,fill=(210,216,226));y+=48
  d.text((30,y+15),f"{data.get('terminal_label','Owner / Master')} · {data.get('account_mode','—')} · {data.get('connection_status','OFFLINE')}",font=font(max(16,W//55)),fill=(155,165,180));y+=75
  row_step=32;section_gap=8
 open_rows=data.get("positions",[])[:5]
 closed_rows=data.get("recent_deals",[])[:5]
 d.text((30,y),"OPEN TRADES",font=head_font,fill=(16,185,129));y+=30
 if open_rows:
  for p in open_rows:
   color=(80,220,150) if safe_number(p.get("profit"))>=0 else (248,113,113)
   d.text((45,y),trade_text(p,c),font=row_font,fill=color);y+=row_step
 else:
  d.text((45,y),"No open trades at this moment",font=row_font,fill=(155,165,180));y+=row_step
 y+=section_gap
 d.text((30,y),"RECENT CLOSED TRADES",font=head_font,fill=(34,211,238));y+=30
 if closed_rows:
  for p in closed_rows:
   color=(80,220,150) if safe_number(p.get("profit"))>=0 else (248,113,113)
   if y>H-72:break
   d.text((45,y),trade_text(p,c),font=row_font,fill=color);y+=row_step
 else:
  d.text((45,y),"No recent closed trades available",font=row_font,fill=(155,165,180))
 footer="MetaTrader EA execution · No trade controls · Past performance does not guarantee future results."
 d.rectangle((0,H-58,W,H),fill=(8,13,22));d.text((30,H-42),footer,font=font(max(12,W//82)),fill=(115,125,140));return im
class Encoder:
 def __init__(self,n,w,h):self.n=n;self.w=w;self.h=h;self.p=None;self.o=ROOT/n;self.sig=()
 def wanted(self,cfg):
  names=("youtube","facebook") if self.n=="landscape" else ("instagram","tiktok")
  return tuple((n,SOCIAL_URLS.get(n,"")) for n in names if cfg.get("destinations",{}).get(n) and SOCIAL_URLS.get(n))

 def start(self,cfg):
  self.stop();self.o.mkdir(parents=True,exist_ok=True);social=self.wanted(cfg);self.sig=social
  hls=str(self.o/"live.m3u8")
  cmd=["ffmpeg","-hide_banner","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{self.w}x{self.h}","-r","2","-i","-","-f","lavfi","-i","anullsrc=channel_layout=stereo:sample_rate=44100","-c:v","libx264","-preset","veryfast","-tune","zerolatency","-pix_fmt","yuv420p","-g","4","-c:a","aac","-b:a","128k"]
  if not social:
   cmd+=["-f","hls","-hls_time","2","-hls_list_size","5","-hls_flags","delete_segments+append_list+omit_endlist",hls]
  else:
   outs=[f"[f=hls:hls_time=2:hls_list_size=5:hls_flags=delete_segments+append_list+omit_endlist]{hls}"]+[f"[f=flv:onfail=ignore]{u}" for _,u in social]
   cmd+=["-map","0:v","-map","1:a","-f","tee","|".join(outs)]
  self.p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 def write(self,im,cfg):
  wanted=self.wanted(cfg)
  if self.p is None or self.p.poll() is not None or wanted!=self.sig:self.start(cfg)
  try:self.p.stdin.write(im.tobytes());self.p.stdin.flush()
  except Exception:self.start(cfg)
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
   if cfg.get("landscape_enabled"):L.write(frame(src,(1280,720)),cfg);runtime["landscape"]=True
   else:L.stop();runtime["landscape"]=False
   if cfg.get("vertical_enabled"):V.write(frame(src,(720,1280)),cfg);runtime["vertical"]=True
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
 return FileResponse(p,media_type='application/vnd.apple.mpegurl',headers={'Cache-Control':'no-store','Access-Control-Allow-Origin':'https://betheltradingtechnologies.com'})
@app.get('/live/{layout}/{segment}')
def segment(layout:str,segment:str):
 if layout not in {'landscape','vertical'} or '/' in segment or '..' in segment:raise HTTPException(404,"Unknown segment")
 p=ROOT/layout/segment
 if not p.exists():raise HTTPException(404,"Segment unavailable")
 return FileResponse(p,media_type='video/mp2t',headers={'Cache-Control':'no-store','Access-Control-Allow-Origin':'https://betheltradingtechnologies.com'})

def _load_media_meta(meta_path):
 try:return json.loads(meta_path.read_text(encoding="utf-8"))
 except Exception:return {}
def _share_active(meta,now_epoch=None):
 now_epoch=int(time.time()) if now_epoch is None else int(now_epoch)
 return bool(meta.get("share_token") and not meta.get("share_revoked",False) and int(meta.get("share_expires_at",0) or 0)>now_epoch)
def _share_status(meta):
 if meta.get("share_revoked",False):return "REVOKED"
 if not meta.get("share_expires_at"):return "LEGACY_EXPIRED"
 if int(meta.get("share_expires_at",0))<=int(time.time()):return "EXPIRED"
 return "ACTIVE" if meta.get("share_token") else "UNAVAILABLE"

@app.post('/media/generate')
def generate_media(payload:dict,x_bethel_broadcast_secret:str=Header(default="")):
 media_auth(x_bethel_broadcast_secret);layout=str(payload.get("layout","landscape")).lower()
 if layout not in {"landscape","vertical"}:raise HTTPException(422,"Unknown media layout")
 duration=max(8,min(60,int(payload.get("duration_seconds",15))));src=get("/broadcast/v1/worker/source")
 if not src.get("available"):raise HTTPException(409,"Owner/master telemetry unavailable")
 size=(1280,720) if layout=="landscape" else (720,1280);im=frame(src,size);stamp=time.strftime("%Y%m%d-%H%M%S",time.gmtime());name=f"bethel-weekly-{layout}-{stamp}-{uuid.uuid4().hex[:16]}.mp4";out=MEDIA_ROOT/name
 cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{size[0]}x{size[1]}","-r","2","-i","-","-f","lavfi","-i","aevalsrc=(0.11+0.03*sin(2*PI*0.18*t))*(sin(2*PI*220*t)+0.72*sin(2*PI*277.18*t)+0.56*sin(2*PI*329.63*t)+0.30*sin(2*PI*440*t)):s=44100","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-filter:a","volume=0.28,afade=t=in:st=0:d=1","-ac","2","-c:a","aac","-b:a","160k","-t",str(duration),"-movflags","+faststart",str(out)]
 p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 for _ in range(duration*2):p.stdin.write(im.tobytes())
 p.stdin.close();p.wait(timeout=45)
 if p.returncode!=0 or not out.exists():raise HTTPException(500,"Media generation failed")
 share_token=uuid.uuid4().hex+uuid.uuid4().hex;share_expires_at=int(time.time())+MEDIA_SHARE_TTL_SECONDS
 meta={"filename":name,"layout":layout,"duration_seconds":duration,"created_at":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"title":f"Bethel Weekly {layout.title()} Update","account_mode":src.get("account_mode"),"read_only":True,"share_token":share_token,"share_expires_at":share_expires_at,"share_revoked":False,"audio":"generated_ambient_music"};(MEDIA_ROOT/(name+".json")).write_text(json.dumps(meta),encoding="utf-8")
 return {**meta,"share_status":"ACTIVE","url":f"https://bethel-broadcast.onrender.com/media/share/{share_token}"}

@app.get('/media/list')
def media_list(x_bethel_broadcast_secret:str=Header(default="")):
 media_auth(x_bethel_broadcast_secret);items=[]
 for mp4 in sorted(MEDIA_ROOT.glob("*.mp4"),key=lambda p:p.stat().st_mtime,reverse=True)[:50]:
  meta=_load_media_meta(MEDIA_ROOT/(mp4.name+".json"));active=_share_active(meta)
  items.append({**meta,"filename":mp4.name,"size_bytes":mp4.stat().st_size,"share_status":_share_status(meta),"url":f"https://bethel-broadcast.onrender.com/media/share/{meta.get('share_token','')}" if active else None})
 return {"items":items,"read_only":True,"share_ttl_seconds":MEDIA_SHARE_TTL_SECONDS}

@app.post('/media/revoke/{token}')
def media_revoke(token:str,x_bethel_broadcast_secret:str=Header(default="")):
 media_auth(x_bethel_broadcast_secret)
 if len(token)!=64 or not all(c in "0123456789abcdef" for c in token.lower()):raise HTTPException(404,"Media unavailable")
 for meta_path in MEDIA_ROOT.glob("*.mp4.json"):
  meta=_load_media_meta(meta_path);stored=str(meta.get("share_token",''))
  if stored and hmac.compare_digest(stored,token):
   meta["share_revoked"]=True;meta_path.write_text(json.dumps(meta),encoding="utf-8")
   return {"status":"revoked","filename":meta.get("filename"),"read_only":True}
 raise HTTPException(404,"Media unavailable")

@app.get('/media/share/{token}')
def media_share(token:str):
 if len(token)!=64 or not all(c in "0123456789abcdef" for c in token.lower()):raise HTTPException(404,"Media unavailable")
 for meta_path in MEDIA_ROOT.glob("*.mp4.json"):
  meta=_load_media_meta(meta_path);stored=str(meta.get("share_token",''))
  if not stored or not hmac.compare_digest(stored,token):continue
  if not _share_active(meta):raise HTTPException(410,"Media review link expired or revoked")
  p=MEDIA_ROOT/meta.get("filename","")
  if not p.exists():raise HTTPException(404,"Media unavailable")
  return FileResponse(p,media_type="video/mp4",filename=p.name,headers={"Cache-Control":"private, no-store","Pragma":"no-cache","X-Robots-Tag":"noindex, nofollow, noarchive"})
 raise HTTPException(404,"Media unavailable")
