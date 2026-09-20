// ARM 2.7: arm26 transport/security/sound plus Phase-3 human mouse ownership.
#define setup arm26_setup
#define loop arm26_loop
#include "../arm26/ams_board26.ino"
#undef setup
#undef loop
#include "human_mouse_v3.h"

void setup(){ arm26_setup(); }
void loop(){
  poll_host_usb();
  if(serial1_line_ready()){
    g_out=&Serial1;
    if(!human_mouse_v3_handle(g_line1)) legacy_handle_unused: handle(g_line1);
    g_out=0;
  }
  if(!g_secure){if(Serial)do_handshake(40);else delay(1);return;}
  if(Serial.available()&&read_line_blocking(50)){
    static char cmd[MAX_PT];
    if(decrypt_to(g_line,cmd,MAX_PT)){g_lastFrameMs=millis();handle(cmd);}
    else if(hello_from_line(g_line)){}
    else{digitalWrite(LED_ERR,LOW);delay(30);digitalWrite(LED_ERR,HIGH);}
  }
  if(SESSION_IDLE_MS&&(millis()-g_lastFrameMs>SESSION_IDLE_MS))session_reset();
}
