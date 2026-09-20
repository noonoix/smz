#pragma once
// Phase 3A: bounded, HALT-abortable human mouse owned by the Pro Micro.
// This file is included after arm26 so it can use its HID, cursor and UART primitives.
struct HumanMouseConfigV3 {
  int speedMin=150,speedMax=500,moveMin=0,moveMax=0;
  int curveMin=15,curveMax=45,beforeMin=120,beforeMax=450,afterMin=150,afterMax=600;
  int midChance=12,midMin=100,midMax=400,idleEveryMin=5,idleEveryMax=12;
  int idlePauseMin=800,idlePauseMax=3000,overChance=15;
  uint16_t movesSinceIdle=0,nextIdle=0;
  bool configured=false;
};
static HumanMouseConfigV3 g_hm3;
static long hm3_rand(long a,long b){ if(b<a){long t=a;a=b;b=t;} return b<=a?a:random(a,b+1); }
static float hm3_clampf(float v,float a,float b){return v<a?a:v>b?b:v;}
static bool hm3_wait(uint32_t ms){
  uint32_t started=millis();
  while(millis()-started<ms){
    poll_host_usb();
    if(serial1_line_ready()){
      if(!strncmp(g_line1,"HALT",4)){do_halt();send_line("ERR|ABORTED|HMOVE");return false;}
      reply_err("BUSY");
    }
    delay(2);
  }
  return true;
}
static bool hm3_leg(int32_t sx,int32_t sy,int32_t tx,int32_t ty,uint32_t duration,float curve){
  float dx=tx-sx,dy=ty-sy,dist=sqrt(dx*dx+dy*dy);
  if(dist<1){SingleAbsoluteMouse.moveTo(toAbsX(tx),toAbsY(ty));g_curX=tx;g_curY=ty;return true;}
  float nx=-dy/dist,ny=dx/dist;
  float side=random(0,2)?1.0f:-1.0f;
  float height=dist*(0.012f+0.0028f*hm3_clampf(curve,0,200));
  // Screen-aware side selection; never flatten by clamping an already-built path.
  float mx=(sx+tx)*0.5f,my=(sy+ty)*0.5f;
  if(mx+nx*height<2||mx+nx*height>g_scrW-3||my+ny*height<2||my+ny*height>g_scrH-3) side=-side;
  uint16_t steps=(uint16_t)constrain((long)(dist/3.0f),12L,96L);
  uint32_t elapsed=0;
  for(uint16_t i=1;i<=steps;i++){
    float t=(float)i/steps;
    float ease=t*t*(3.0f-2.0f*t); // acceleration + deceleration
    float arc=sin(PI*t)*height*side;
    int32_t px=(int32_t)round(sx+dx*ease+nx*arc);
    int32_t py=(int32_t)round(sy+dy*ease+ny*arc);
    if(px<0)px=0;if(px>=g_scrW)px=g_scrW-1;if(py<0)py=0;if(py>=g_scrH)py=g_scrH-1;
    SingleAbsoluteMouse.moveTo(toAbsX(px),toAbsY(py));g_curX=px;g_curY=py;
    uint32_t target=(uint32_t)((duration*(uint32_t)i)/steps);
    if(target>elapsed&&!hm3_wait(target-elapsed))return false;
    elapsed=target;
  }
  g_curX=tx;g_curY=ty;SingleAbsoluteMouse.moveTo(toAbsX(tx),toAbsY(ty));return true;
}
static bool hm3_move(int32_t tx,int32_t ty){
  if(!g_hm3.configured){reply_err("HMOUSE|NOCFG");return false;}
  if(!hm3_wait((uint32_t)hm3_rand(g_hm3.beforeMin,g_hm3.beforeMax)))return false;
  int32_t sx=g_curX,sy=g_curY;float dx=tx-sx,dy=ty-sy,dist=sqrt(dx*dx+dy*dy);
  long duration;
  if(g_hm3.moveMax>0) duration=hm3_rand(g_hm3.moveMin,g_hm3.moveMax);
  else {long speed=max(1L,hm3_rand(g_hm3.speedMin,g_hm3.speedMax));duration=(long)(dist*1000.0f/speed);}
  duration=constrain(duration,1L,30000L);
  float curve=(float)hm3_rand(g_hm3.curveMin,g_hm3.curveMax);
  bool over=dist>=80&&g_hm3.overChance>0&&random(0,100)<g_hm3.overChance;
  if(over){
    float ux=dx/max(1.0f,dist),uy=dy/max(1.0f,dist);
    long extra=constrain((long)(dist*(0.03f+random(0,5001)/100000.0f)),2L,20L);
    int32_t ox=tx+(int32_t)(ux*extra-uy*hm3_rand(-3,3));
    int32_t oy=ty+(int32_t)(uy*extra+ux*hm3_rand(-3,3));
    if(!hm3_leg(sx,sy,ox,oy,(uint32_t)(duration*4/5),curve))return false;
    if(!hm3_wait((uint32_t)hm3_rand(60,180)))return false;
    if(!hm3_leg(ox,oy,tx,ty,(uint32_t)max(1L,duration/5),curve*0.45f))return false;
  } else if(!hm3_leg(sx,sy,tx,ty,(uint32_t)duration,curve))return false;
  if(g_hm3.midChance>0&&random(0,100)<g_hm3.midChance&&!hm3_wait((uint32_t)hm3_rand(g_hm3.midMin,g_hm3.midMax)))return false;
  if(!hm3_wait((uint32_t)hm3_rand(g_hm3.afterMin,g_hm3.afterMax)))return false;
  g_hm3.movesSinceIdle++;
  if(!g_hm3.nextIdle)g_hm3.nextIdle=max(1L,hm3_rand(g_hm3.idleEveryMin,g_hm3.idleEveryMax));
  if(g_hm3.movesSinceIdle>=g_hm3.nextIdle){g_hm3.movesSinceIdle=0;g_hm3.nextIdle=max(1L,hm3_rand(g_hm3.idleEveryMin,g_hm3.idleEveryMax));if(!hm3_wait((uint32_t)hm3_rand(g_hm3.idlePauseMin,g_hm3.idlePauseMax)))return false;}
  reply_ok("HMOVE");return true;
}
static bool human_mouse_v3_handle(char* line){
  char* args=strchr(line,'|'); if(args)*args++=0;else args=(char*)"";
  if(!strcmp(line,"HCFG")){
    int n=sscanf(args,"%d,%d,%d,%d,%d,%d,%d,%d,%d,%d",&g_hm3.speedMin,&g_hm3.speedMax,&g_hm3.moveMin,&g_hm3.moveMax,&g_hm3.curveMin,&g_hm3.curveMax,&g_hm3.beforeMin,&g_hm3.beforeMax,&g_hm3.afterMin,&g_hm3.afterMax);
    if(n!=10){reply_err("HCFG|ARG");return true;} g_hm3.configured=false;reply_ok("HCFG");return true;
  }
  if(!strcmp(line,"HPAUSE")){
    int n=sscanf(args,"%d,%d,%d,%d,%d,%d,%d,%d",&g_hm3.midChance,&g_hm3.midMin,&g_hm3.midMax,&g_hm3.idleEveryMin,&g_hm3.idleEveryMax,&g_hm3.idlePauseMin,&g_hm3.idlePauseMax,&g_hm3.overChance);
    if(n!=8){reply_err("HPAUSE|ARG");return true;} g_hm3.configured=true;reply_ok("HPAUSE");return true;
  }
  if(!strcmp(line,"HMOVE")){int x,y;if(sscanf(args,"%d,%d",&x,&y)!=2)reply_err("HMOVE|ARG");else hm3_move(x,y);return true;}
  if(!strcmp(line,"HRANDOM")){int x,y,w,h;if(sscanf(args,"%d,%d,%d,%d",&x,&y,&w,&h)!=4||w<1||h<1)reply_err("HRANDOM|ARG");else hm3_move(hm3_rand(x,x+w-1),hm3_rand(y,y+h-1));return true;}
  return false;
}
