#!/usr/bin/env python3
"""Write an application-only Intel HEX to an ATmega32U4 via ArduinoISP.

Safety contract: the HEX must end below 0x7000. No chip erase, fuse write,
lock write, EEPROM write, or bootloader-page write is performed.
"""
import argparse, os, sys, time

STK_INSYNC=0x14; STK_OK=0x10; CRC_EOP=0x20
CMD_GET_SYNC=0x30; CMD_SET_DEVICE=0x42; CMD_ENTER=0x50; CMD_LEAVE=0x51
CMD_LOAD_ADDRESS=0x55; CMD_UNIVERSAL=0x56; CMD_PROG_PAGE=0x64
CMD_READ_PAGE=0x74; CMD_READ_SIGN=0x75
FLASH_SIZE=0x8000; PAGE_SIZE=128; BOOT_START=0x7000
SIG=bytes((0x1E,0x95,0x87))

class ISPError(Exception): pass

def log(s=''): print(s, flush=True)

class STK500:
    def __init__(self, port):
        try:
            import serial
            self.s=serial.Serial(port,19200,timeout=2,write_timeout=2)
            self.s.dtr=True; self.s.rts=True; time.sleep(1); self.s.reset_input_buffer()
        except Exception as e: raise ISPError(f"cannot open {port}: {e}")
    def close(self):
        try: self.s.close()
        except Exception: pass
    def exact(self,n,what):
        b=self.s.read(n)
        if len(b)!=n: raise ISPError(f"timeout reading {what} ({len(b)}/{n})")
        return b
    def cmd(self,payload,n=0,what='command'):
        self.s.reset_input_buffer(); self.s.write(bytes(payload)+(CRC_EOP,))
        if self.exact(1,what)[0]!=STK_INSYNC: raise ISPError(f"not in sync during {what}")
        data=self.exact(n,what) if n else b''
        if self.exact(1,what)[0]!=STK_OK: raise ISPError(f"{what} failed")
        return data
    def sync(self):
        for _ in range(15):
            try: self.cmd([CMD_GET_SYNC],what='sync'); return
            except ISPError: time.sleep(.2)
        raise ISPError('no sync with ArduinoISP')
    def setup(self):
        params=[0x44,0,0,1,1,1,1,3,0xFF,0xFF,0xFF,0xFF,0,0x80,4,0,0,0,0x80,0]
        self.cmd([CMD_SET_DEVICE]+params,what='set device'); self.cmd([CMD_ENTER],what='enter programming mode')
    def leave(self): self.cmd([CMD_LEAVE],what='leave programming mode')
    def sig(self): return self.cmd([CMD_READ_SIGN],3,'signature')
    def universal(self,a,b,c,d): return self.cmd([CMD_UNIVERSAL,a,b,c,d],1,'universal')[0]
    def addr(self,byte_addr):
        w=byte_addr//2; self.cmd([CMD_LOAD_ADDRESS,w&255,(w>>8)&255],what='load address')
    def write_page(self,addr,data):
        self.addr(addr); n=len(data); self.cmd([CMD_PROG_PAGE,n>>8,n&255,ord('F')]+list(data),what=f'write 0x{addr:04X}')
    def read_page(self,addr,n):
        self.addr(addr); return self.cmd([CMD_READ_PAGE,n>>8,n&255,ord('F')],n,'read page')

def parse_hex(path):
    image=bytearray(b'\xff'*FLASH_SIZE); base=0; lo=None; hi=None
    for raw in open(path,encoding='ascii',errors='replace'):
        line=raw.strip()
        if not line or not line.startswith(':'): continue
        r=bytes.fromhex(line[1:])
        if sum(r)&255: raise ISPError('bad Intel HEX checksum')
        n=(r[0]); a=(r[1]<<8)|r[2]; typ=r[3]
        if typ==0:
            start=base+a
            if start+n>FLASH_SIZE: raise ISPError('HEX exceeds ATmega32U4 flash')
            image[start:start+n]=r[4:4+n]
            lo=start if lo is None else min(lo,start); hi=start+n-1 if hi is None else max(hi,start+n-1)
        elif typ==4: base=((r[4]<<8)|r[5])<<16
        elif typ==1: break
    if lo is None: raise ISPError('HEX contains no data')
    return image,lo,hi

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--port',required=True); ap.add_argument('--hex',required=True)
    ap.add_argument('--app-only',action='store_true',required=True)
    args=ap.parse_args()
    image,lo,hi=parse_hex(args.hex)
    if lo<0 or hi>=BOOT_START:
        raise SystemExit(f'REFUSED: application HEX range 0x{lo:04X}-0x{hi:04X} reaches bootloader (0x7000)')
    stk=None
    try:
        log('='*60); log('AMS Application ISP Flasher — bootloader preserved'); log('='*60)
        log('[Step 1] Sync with ArduinoISP...'); stk=STK500(args.port); stk.sync(); log('sync OK (14 10)'); stk.setup(); log('programming mode entered')
        log('[Step 2] Target signature...'); sig=stk.sig(); log('signature = 0x'+sig.hex())
        if sig!=SIG: raise ISPError('unexpected signature; expected 0x1e9587')
        log('[Step 3] Safety check: no chip erase, no fuses, no lock, no EEPROM, no bootloader writes')
        first=lo & ~(PAGE_SIZE-1); last=hi & ~(PAGE_SIZE-1); pages=list(range(first,last+1,PAGE_SIZE))
        log(f'[Step 4] Application image range 0x{lo:04X}-0x{hi:04X}')
        log(f'[Step 5] Writing {len(pages)} application pages...')
        for i,p in enumerate(pages,1):
            stk.write_page(p,bytes(image[p:p+PAGE_SIZE]))
            if i%10==0 or i==len(pages): log(f'wrote page @0x{p:04X} ({i}/{len(pages)})')
        log('[Step 6] Verifying application pages...')
        for p in pages:
            if stk.read_page(p,PAGE_SIZE)!=bytes(image[p:p+PAGE_SIZE]): raise ISPError(f'verify failed at 0x{p:04X}')
        log('verify OK - application is on target; bootloader was not touched')
        stk.leave(); log('='*60); log('APPLICATION ISP FLASH COMPLETE'); log('='*60)
    except Exception as e:
        log('ERROR: '+str(e)); sys.exit(1)
    finally:
        if stk: stk.close()
if __name__=='__main__': main()
