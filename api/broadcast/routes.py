from datetime import datetime, timezone
import hmac, os
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from api.auth.dependency import require_super_admin
from api.database import SessionLocal
from api.broadcast.models import BroadcastControl
from api.mt5_ingest.models import ConnectorDeal, ConnectorPosition, ConnectorStatus, MasterTerminalRegistry

router=APIRouter(prefix="/broadcast/v1",tags=["Read-only broadcast engine"])
def now(): return datetime.now(timezone.utc).replace(tzinfo=None)
def ctl(db):
    BroadcastControl.__table__.create(bind=db.get_bind(),checkfirst=True)
    x=db.query(BroadcastControl).filter(BroadcastControl.id==1).first()
    if x is None:
        x=BroadcastControl(id=1,enabled=False); db.add(x); db.commit(); db.refresh(x)
    return x
def worker_auth(x_bethel_broadcast_secret:str=Header(default="")):
    exp=os.getenv("BROADCAST_WORKER_SECRET","")
    if len(exp)<64: raise HTTPException(503,"Broadcast worker secret is not configured")
    if not x_bethel_broadcast_secret or not hmac.compare_digest(x_bethel_broadcast_secret,exp): raise HTTPException(401,"Invalid broadcast worker authentication")
    return True
class BroadcastUpdate(BaseModel):
    enabled: bool
    terminal_registry_id: int|None=Field(default=None,gt=0)
    landscape_enabled: bool=True
    vertical_enabled: bool=True
    website_enabled: bool=False
    youtube_enabled: bool=False
    facebook_enabled: bool=False
    instagram_enabled: bool=False
    tiktok_enabled: bool=False
    confirm_start: bool=False
class Heartbeat(BaseModel):
    state:str=Field(min_length=2,max_length=32)
    message:str|None=Field(default=None,max_length=255)
def dump(x):
    return {"enabled":bool(x.enabled),"terminal_registry_id":x.terminal_registry_id,"landscape_enabled":bool(x.landscape_enabled),"vertical_enabled":bool(x.vertical_enabled),"website_enabled":bool(x.website_enabled),"destinations":{"youtube":bool(x.youtube_enabled),"facebook":bool(x.facebook_enabled),"instagram":bool(x.instagram_enabled),"tiktok":bool(x.tiktok_enabled)},"worker_state":x.worker_state,"worker_message":x.worker_message,"worker_last_seen":x.worker_last_seen.isoformat()+"Z" if x.worker_last_seen else None,"read_only":True,"execution_owner":"METATRADER_EA"}
@router.get('/admin/control')
def get_control(_=Depends(require_super_admin)):
    db=SessionLocal()
    try:return dump(ctl(db))
    finally:db.close()
@router.put('/admin/control')
def set_control(data:BroadcastUpdate,_=Depends(require_super_admin)):
    db=SessionLocal()
    try:
        x=ctl(db)
        if data.enabled:
            if not data.confirm_start: raise HTTPException(422,"Explicit Super Admin broadcast confirmation is required")
            if data.terminal_registry_id is None: raise HTTPException(422,"Select an owner/master terminal before starting broadcast")
            t=db.query(MasterTerminalRegistry).filter(MasterTerminalRegistry.id==data.terminal_registry_id,MasterTerminalRegistry.active.is_(True),MasterTerminalRegistry.subscriber_id.is_(None)).first()
            if t is None: raise HTTPException(403,"Only active owner/master terminals can be broadcast")
            if not data.landscape_enabled and not data.vertical_enabled: raise HTTPException(422,"Enable at least one video layout")
            x.terminal_registry_id=t.id
        x.enabled=data.enabled; x.landscape_enabled=data.landscape_enabled; x.vertical_enabled=data.vertical_enabled; x.website_enabled=data.website_enabled
        x.youtube_enabled=data.youtube_enabled
        x.facebook_enabled=data.facebook_enabled
        x.instagram_enabled=data.instagram_enabled
        x.tiktok_enabled=data.tiktok_enabled
        if not data.enabled: x.worker_state='STOPPING'; x.worker_message='Broadcast disabled by Super Admin'
        db.commit(); db.refresh(x); return dump(x)
    finally:db.close()
@router.get('/public/status')
def public_status():
    db=SessionLocal()
    try:
        x=ctl(db)
        live=bool(x.enabled and x.website_enabled and x.worker_state=='STREAMING')
        return {'enabled':live,'layout':'landscape','hls_url':'https://bethel-broadcast.onrender.com/live/landscape/live.m3u8' if live else None,'read_only':True}
    finally:db.close()
@router.get('/worker/config')
def worker_config(_=Depends(worker_auth)):
    db=SessionLocal()
    try:return dump(ctl(db))
    finally:db.close()
@router.get('/worker/source')
def worker_source(_=Depends(worker_auth)):
    db=SessionLocal()
    try:
        x=ctl(db)
        if not x.enabled or not x.terminal_registry_id:return {"enabled":False,"read_only":True}
        reg=db.query(MasterTerminalRegistry).filter(MasterTerminalRegistry.id==x.terminal_registry_id,MasterTerminalRegistry.active.is_(True),MasterTerminalRegistry.subscriber_id.is_(None)).first()
        if reg is None: raise HTTPException(409,"Broadcast source unavailable")
        st=db.query(ConnectorStatus).filter(ConnectorStatus.connector_id==reg.connector_id).first()
        if st is None:return {"enabled":True,"available":False,"read_only":True}
        pos=db.query(ConnectorPosition).filter(ConnectorPosition.connector_id==reg.connector_id).order_by(ConnectorPosition.observed_at.desc()).limit(8).all()
        deals=db.query(ConnectorDeal).filter(ConnectorDeal.connector_id==reg.connector_id).order_by(ConnectorDeal.closed_at.desc()).limit(8).all()
        age=max(0,int((now()-st.received_at).total_seconds()))
        return {"enabled":True,"available":True,"read_only":True,"execution_owner":"METATRADER_EA","terminal_label":reg.label,"account_mode":st.mode,"currency":st.currency,"connection_status":"ONLINE" if age<=150 else "STALE","balance":st.balance,"equity":st.equity,"floating_profit":st.floating_profit,"open_position_count":len(pos),"positions":[{"symbol":p.symbol,"direction":p.direction,"volume":p.volume,"profit":p.profit} for p in pos],"recent_deals":[{"symbol":d.symbol,"direction":d.deal_type,"volume":d.volume,"profit":d.profit,"closed_at":d.closed_at.isoformat()+"Z" if d.closed_at else None} for d in deals]}
    finally:db.close()
@router.post('/worker/heartbeat')
def heartbeat(data:Heartbeat,_=Depends(worker_auth)):
    db=SessionLocal()
    try:
        x=ctl(db); x.worker_state=data.state.upper(); x.worker_message=data.message; x.worker_last_seen=now(); db.commit(); return {"status":"accepted"}
    finally:db.close()
