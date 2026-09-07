#!/usr/bin/env python3
r"""
isp_flash.py -- Pure-Python ISP recovery for a bricked ATmega32U4 (AMS board)
via an ArduinoISP programmer board. No avrdude needed.

WHY THIS EXISTS
---------------
avrdude 6.3 (bundled with Arduino IDE 1.8.x) cannot sync with ArduinoISP
running on 32U4 boards (Leonardo / Pro Micro) on Windows: it opens the
serial port without properly asserting DTR ("host ready"), and the 32U4's
USB stack then drops the sketch's replies. Result: the infamous
    stk500_getsync() attempt N of 10: not in sync: resp=0x03
pyserial asserts DTR correctly, so this script just speaks stk500v1 to the
ArduinoISP sketch directly. Proven on the user's setup: sync returns 14 10.

WHAT IT DOES (full run)
-----------------------
    1. sync with ArduinoISP, set device params, enter programming mode
    2. read target signature (must be 1E 95 87 = ATmega32U4)
    3. back up target flash + eeprom to .bin files
    4. read fuses + lock, report
    5. write Caterina.hex (page erase+write per page, then verify)
    6. optionally fix fuses to FF/D8/CB (--fix-fuses)
    7. set lock = 0x2F so the bootloader can never self-destruct again
    8. leave programming mode

USAGE
-----
    python isp_flash.py --port COM11 --check-only     # read-only diagnosis
    python isp_flash.py --port COM11                  # full recovery
    python isp_flash.py --port COM11 --fix-fuses      # also repair fuses
    python isp_flash.py --selftest                    # offline protocol test

Place this file next to the caterina\Caterina.hex folder (e.g. in
_help-from-ai). No third step needed.
"""

import argparse
import hashlib
import os
import sys
import time

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

STK_INSYNC = 0x14
STK_OK = 0x10
STK_NOSYNC = 0x15
CRC_EOP = 0x20

CMD_GET_SYNC = 0x30       # '0'
CMD_SET_DEVICE = 0x42     # 'B'
CMD_ENTER_PROGMODE = 0x50 # 'P'
CMD_LEAVE_PROGMODE = 0x51 # 'Q'
CMD_LOAD_ADDRESS = 0x55   # 'U'  (word address, low byte first)
CMD_UNIVERSAL = 0x56      # 'V'
CMD_PROG_PAGE = 0x64
CMD_READ_PAGE = 0x74
CMD_READ_SIGN = 0x75

FLASH_SIZE = 0x8000       # 32 KB
PAGE_SIZE = 128
EEPROM_SIZE = 1024
BOOT_START = 0x7000

EXPECTED_SIGNATURE = bytes([0x1E, 0x95, 0x87])
EXPECTED_FUSES = {"lfuse": 0xFF, "hfuse": 0xD8, "efuse": 0xCB}
SAFE_LOCK = 0x2F          # BLB1=10: SPM may not write the boot section

KNOWN_GOOD_CATERINA_MD5 = "fa2f7afb6a20a388b93728044ae97b97"


class ISPError(Exception):
    pass


# --------------------------------------------------------------------------
# stk500v1 client (talks to the ArduinoISP sketch)
# --------------------------------------------------------------------------

class STK500:
    def __init__(self, port=None, baud=19200, ser=None):
        if ser is not None:
            self.ser = ser                      # mock / selftest
        else:
            import serial                       # lazy: only needed on hardware
            try:
                self.ser = serial.Serial()
                self.ser.port = port
                self.ser.baudrate = baud        # ignored by USB CDC, harmless
                self.ser.timeout = 2
                self.ser.write_timeout = 2
                self.ser.open()
            except serial.SerialException as e:
                raise ISPError(
                    "cannot open %s: %s\n"
                    "  -> close Arduino IDE / Serial Monitor completely,\n"
                    "     or unplug+replug the programmer board." % (port, e))
            self.ser.dtr = True                 # THE fix vs avrdude
            self.ser.rts = True
            time.sleep(1.0)
            self.ser.reset_input_buffer()

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass

    # -- low level ---------------------------------------------------------

    def _read_exact(self, n, what="response"):
        data = self.ser.read(n)
        if len(data) < n:
            raise ISPError("timeout reading %s (got %d/%d bytes)"
                           % (what, len(data), n))
        return data

    def command(self, payload, resp_len=0, what="command"):
        self.ser.reset_input_buffer()
        self.ser.write(bytes(payload) + bytes([CRC_EOP]))
        first = self._read_exact(1, what)[0]
        if first != STK_INSYNC:
            raise ISPError("not in sync during %s (got 0x%02X)" % (what, first))
        data = self._read_exact(resp_len, what) if resp_len else b""
        ok = self._read_exact(1, what)[0]
        if ok != STK_OK:
            raise ISPError("%s failed (status 0x%02X)" % (what, ok))
        return data

    # -- high level --------------------------------------------------------

    def sync(self, attempts=15):
        for i in range(attempts):
            try:
                self.command([CMD_GET_SYNC], what="sync")
                return True
            except ISPError:
                time.sleep(0.2)
        return False

    def set_device(self):
        # ATmega32U4 parameters, 20 bytes (big-endian fields per sketch)
        params = [
            0x44,               # devicecode (32U4)
            0x00,               # revision
            0x00,               # progtype: serial
            0x01,               # parmode
            0x01,               # polling
            0x01,               # selftimed
            0x01,               # lockbytes
            0x03,               # fusebytes
            0xFF, 0xFF,         # flashpoll (x2)
            0xFF, 0xFF,         # eeprompoll
            0x00, 0x80,         # pagesize   = 128
            0x04, 0x00,         # eepromsize = 1024
            0x00, 0x00, 0x80, 0x00,  # flashsize = 32768
        ]
        assert len(params) == 20
        self.command([CMD_SET_DEVICE] + params, what="set device params")

    def enter_progmode(self):
        self.command([CMD_ENTER_PROGMODE], what="enter programming mode")

    def leave_progmode(self):
        self.command([CMD_LEAVE_PROGMODE], what="leave programming mode")

    def read_signature(self):
        return self.command([CMD_READ_SIGN], resp_len=3, what="read signature")

    def universal(self, a, b, c, d):
        return self.command([CMD_UNIVERSAL, a, b, c, d], resp_len=1,
                            what="universal")[0]

    def load_address(self, byte_addr):
        w = byte_addr >> 1                        # word address
        self.command([CMD_LOAD_ADDRESS, w & 0xFF, (w >> 8) & 0xFF],
                     what="load address")

    def prog_page(self, byte_addr, data):
        n = len(data)
        assert n % 2 == 0 and n <= 256
        self.load_address(byte_addr)
        self.command([CMD_PROG_PAGE, (n >> 8) & 0xFF, n & 0xFF, ord('F')]
                     + list(data), what="program page @0x%04X" % byte_addr)

    def read_page(self, byte_addr, length, mem="F"):
        self.load_address(byte_addr)
        return self.command([CMD_READ_PAGE, (length >> 8) & 0xFF,
                             length & 0xFF, ord(mem)],
                            resp_len=length, what="read page")

    # -- fuse / lock helpers (ISP instruction set via STK_UNIVERSAL) -------

    def read_fuses(self):
        return {
            "lfuse": self.universal(0x50, 0x00, 0x00, 0x00),
            "hfuse": self.universal(0x58, 0x08, 0x00, 0x00),
            "efuse": self.universal(0x50, 0x08, 0x00, 0x00),
        }

    def read_lock(self):
        return self.universal(0x58, 0x00, 0x00, 0x00)

    def write_fuse(self, name, value):
        op = {"lfuse": (0xAC, 0xA0), "hfuse": (0xAC, 0xA8),
              "efuse": (0xAC, 0xA4)}[name]
        self.universal(op[0], op[1], 0x00, value)
        time.sleep(0.05)                          # tWD_FUSE

    def write_lock(self, value):
        self.universal(0xAC, 0xE0, 0x00, value)
        time.sleep(0.05)

    def chip_erase(self):
        self.universal(0xAC, 0x80, 0x00, 0x00)
        time.sleep(0.5)                           # chip erase takes ~10-20 ms


def ensure_lock(stk, args):
    """Set lock=0x2F with retries. Non-fatal on failure: the bootloader is
    already recovered at this point; the lock is the seatbelt, not the engine.
    The read right after a lock write is unreliable on the 32U4, so we wait
    longer and re-read several times before believing a mismatch."""
    lock = stk.read_lock()
    log("  current lock = 0x%02X" % lock)
    if lock == SAFE_LOCK:
        log("  already 0x2F. Nothing to do.")
        return True
    if args.no_lock:
        log("  skipped (--no-lock).")
        return False
    if (lock & SAFE_LOCK) != SAFE_LOCK:
        log("  WARNING: current lock 0x%02X cannot become 0x2F without a chip "
            "erase." % lock)
        log("  Re-run the full recovery with --erase.")
        return False
    for attempt in range(1, 4):
        stk.write_lock(SAFE_LOCK)
        time.sleep(0.15)                        # let the write latch (tWD_FUSE)
        for _ in range(3):
            lock = stk.read_lock()
            if lock == SAFE_LOCK:
                break
            time.sleep(0.05)
        log("  attempt %d: read-back = 0x%02X" % (attempt, lock))
        if lock == SAFE_LOCK:
            log("  lock = 0x2F set. Bootloader self-destruction is now "
                "impossible.")
            return True
    log("  WARNING: lock write did not confirm (last read 0x%02X)." % lock)
    log("  Right-after-write lock reads are unreliable on the 32U4. Power-")
    log("  cycle the TARGET board, then run:  --lock-only   to check/set it.")
    return False


# --------------------------------------------------------------------------
# Intel HEX
# --------------------------------------------------------------------------

def parse_intel_hex(path):
    image = bytearray(b"\xFF" * FLASH_SIZE)
    lo = hi = None
    base = 0
    with open(path, "r", encoding="ascii", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or not line.startswith(":"):
                continue
            rec = bytes.fromhex(line[1:])
            if sum(rec) & 0xFF != 0:
                raise ISPError("bad checksum in hex line: %s" % line)
            count, addr, rtype = rec[0], (rec[1] << 8) | rec[2], rec[3]
            if rtype == 0x00:
                start = base + addr
                if start + count > FLASH_SIZE:
                    raise ISPError("hex exceeds flash size at 0x%X" % start)
                image[start:start + count] = rec[4:4 + count]
                lo = start if lo is None else min(lo, start)
                hi = start + count - 1 if hi is None else max(hi,
                                                              start + count - 1)
            elif rtype == 0x04:
                base = ((rec[4] << 8) | rec[5]) << 16
            elif rtype == 0x01:
                break
    if lo is None:
        raise ISPError("hex file contains no data")
    return image, lo, hi


# --------------------------------------------------------------------------
# Recovery flow
# --------------------------------------------------------------------------

def log(msg=""):
    print(msg, flush=True)


def recover(stk, args):
    log("=" * 60)
    log("AMS Board ISP Recovery (pure-python stk500v1)")
    log("=" * 60)

    log("\n[Step 1] Sync with ArduinoISP...")
    if not stk.sync():
        raise ISPError(
            "no sync with ArduinoISP sketch.\n"
            "  -> is the sketch really on the programmer? (python direct test\n"
            "     returned 1410 earlier, so this should not happen)")
    log("  sync OK (14 10)")

    stk.set_device()
    stk.enter_progmode()
    log("  programming mode entered (target held in reset via D10)")

    log("\n[Step 2] Target signature...")
    sig = stk.read_signature()
    log("  signature = 0x%s" % sig.hex())
    if sig != EXPECTED_SIGNATURE:
        if sig == b"\x00\x00\x00":
            raise ISPError(
                "signature 0x000000 = target silent. Check, in order:\n"
                "  1. MISO/MOSI (D14/D16) not swapped\n"
                "  2. programmer D10 -> target RST connected\n"
                "  3. target powered (5V + GND)\n"
                "  4. wires short and firmly seated")
        raise ISPError("unexpected signature 0x%s (expected 1e9587)"
                       % sig.hex())
    log("  ATmega32U4 confirmed. Communication OK!")

    fuses = stk.read_fuses()
    lock = stk.read_lock()
    log("\n[Step 3] Fuses & lock (read-only):")
    for name in ("lfuse", "hfuse", "efuse"):
        want = EXPECTED_FUSES[name]
        got = fuses[name]
        mark = "OK" if got == want else "DIFFERS (expected 0x%02X)" % want
        log("  %-6s = 0x%02X  %s" % (name, got, mark))
    log("  lock   = 0x%02X  (target after recovery: 0x%02X)" % (lock, SAFE_LOCK))

    if args.check_only:
        stk.leave_progmode()
        log("\nCheck-only done. Everything read, nothing written.")
        return True

    if not args.no_backup:
        ts = time.strftime("%Y%m%d-%H%M%S")
        log("\n[Step 4] Backup of current flash + eeprom...")
        flash_dump = bytearray()
        for addr in range(0, FLASH_SIZE, PAGE_SIZE):
            flash_dump += stk.read_page(addr, PAGE_SIZE, "F")
            if addr % 0x1000 == 0:
                log("  flash 0x%04X..." % addr)
        fname = "backup-flash-%s.bin" % ts
        with open(fname, "wb") as f:
            f.write(flash_dump)
        ee_dump = bytearray()
        for addr in range(0, EEPROM_SIZE, PAGE_SIZE):
            ee_dump += stk.read_page(addr, PAGE_SIZE, "E")
        ename = "backup-eeprom-%s.bin" % ts
        with open(ename, "wb") as f:
            f.write(ee_dump)
        log("  saved: %s, %s" % (fname, ename))

    image, lo, hi = parse_intel_hex(args.hex)
    md5 = hashlib.md5(open(args.hex, "rb").read()).hexdigest()
    log("\n[Step 5] Bootloader image: %s" % args.hex)
    log("  range 0x%04X-0x%04X, md5 %s%s" % (
        lo, hi, md5,
        " (known-good AMS Caterina)" if md5 == KNOWN_GOOD_CATERINA_MD5 else ""))
    if lo < BOOT_START:
        raise ISPError(
            "this hex writes below 0x7000 - it is an APPLICATION image,\n"
            "  not a bootloader. Refusing (use --hex caterina/Caterina.hex).")

    if args.erase:
        log("\n[Step 6] Chip erase (--erase given). This wipes flash+eeprom.")
        stk.chip_erase()
        log("  erased. (backup was made first)")

    first_page = lo & ~(PAGE_SIZE - 1)
    last_page = hi & ~(PAGE_SIZE - 1)
    pages = list(range(first_page, last_page + 1, PAGE_SIZE))
    log("\n[Step 7] Writing %d flash pages..." % len(pages))
    for i, page in enumerate(pages):
        stk.prog_page(page, bytes(image[page:page + PAGE_SIZE]))
        if (i + 1) % 5 == 0 or i == len(pages) - 1:
            log("  wrote page @0x%04X (%d/%d)" % (page, i + 1, len(pages)))

    log("\n[Step 8] Verifying...")
    bad = 0
    for page in pages:
        got = stk.read_page(page, PAGE_SIZE, "F")
        want = bytes(image[page:page + PAGE_SIZE])
        if got != want:
            bad += 1
            log("  MISMATCH @0x%04X" % page)
    if bad:
        raise ISPError("verification failed on %d page(s). Safe to retry."
                       % bad)
    log("  verify OK - Caterina is on the target.")

    wrong = {k: v for k, v in fuses.items() if v != EXPECTED_FUSES[k]}
    if wrong:
        if args.fix_fuses:
            log("\n[Step 9] Fixing fuses: %s" %
                ", ".join("%s 0x%02X->0x%02X" % (k, v, EXPECTED_FUSES[k])
                           for k, v in wrong.items()))
            for k in wrong:
                stk.write_fuse(k, EXPECTED_FUSES[k])
            fuses = stk.read_fuses()
            if fuses != EXPECTED_FUSES:
                raise ISPError("fuse write did not stick: %s" % fuses)
            log("  fuses now FF/D8/CB. OK.")
        else:
            log("\n[Step 9] WARNING: fuses differ from Leonardo standard:")
            for k, v in wrong.items():
                log("  %s = 0x%02X (expected 0x%02X)" % (k, v,
                                                         EXPECTED_FUSES[k]))
            log("  The bootloader may not start. Re-run with --fix-fuses.")
    else:
        log("\n[Step 9] Fuses already correct (FF/D8/CB).")

    log("\n[Step 10] Lock byte...")
    lock_ok = ensure_lock(stk, args)

    stk.leave_progmode()
    log("\n" + "=" * 60)
    log("RECOVERY COMPLETE!" if lock_ok else
        "FLASH RECOVERED! (lock byte needs one follow-up - see above)")
    log("=" * 60)
    log("Next:")
    log("  1. unplug the target board from the programmer wires")
    log("  2. plug the target's OWN USB cable in (rear-panel USB 2.0 port)")
    log("  3. it should enumerate as your AMS device (VID 1D50 / PID 615E)")
    log("  4. reflash your application firmware with your flash tool")
    return True


# --------------------------------------------------------------------------
# Selftest: emulate ArduinoISP + a bricked target, run the whole flow
# --------------------------------------------------------------------------

class MockSerial:
    """Byte-level emulation of the ArduinoISP sketch on a bricked 32U4."""

    def __init__(self):
        self.flash = bytearray(b"\xFF" * FLASH_SIZE)
        for i in range(BOOT_START, FLASH_SIZE):      # destroyed boot section
            self.flash[i] = 0x55
        self.eeprom = bytearray(b"\xAA" * EEPROM_SIZE)
        self.fuses = dict(EXPECTED_FUSES)
        self.lock = 0xFF
        self.here = 0
        self.rx = bytearray()
        self.dtr = self.rts = True
        self.timeout = 2

    # pyserial surface used by STK500
    def reset_input_buffer(self):
        self.rx.clear()

    def read(self, n=1):
        out = bytes(self.rx[:n])
        del self.rx[:n]
        return out

    def write(self, data):
        buf = bytes(data)
        assert buf[-1] == CRC_EOP, "command without EOP"
        self._handle(buf[:-1])
        return len(data)

    def close(self):
        pass

    # sketch emulation
    def _reply(self, *bs):
        self.rx += bytes(bs)

    def _handle(self, c):
        op = c[0]
        if op == CMD_GET_SYNC:
            self._reply(STK_INSYNC, STK_OK)
        elif op == CMD_SET_DEVICE and len(c) == 21:
            assert ((c[13] << 8) | c[14]) == 128, "pagesize must be 128 BE"
            self._reply(STK_INSYNC, STK_OK)
        elif op == CMD_ENTER_PROGMODE or op == CMD_LEAVE_PROGMODE:
            self._reply(STK_INSYNC, STK_OK)
        elif op == CMD_LOAD_ADDRESS:
            self.here = c[1] | (c[2] << 8)
            self._reply(STK_INSYNC, STK_OK)
        elif op == CMD_READ_SIGN:
            self._reply(STK_INSYNC, *EXPECTED_SIGNATURE, STK_OK)
        elif op == CMD_UNIVERSAL:
            self._universal(c[1], c[2], c[3], c[4])
        elif op == CMD_PROG_PAGE:
            n = (c[1] << 8) | c[2]
            assert c[3] == ord('F') and len(c) == 4 + n
            data = c[4:]
            for i in range(0, n, 2):
                self.flash[self.here * 2] = data[i]
                self.flash[self.here * 2 + 1] = data[i + 1]
                self.here += 1
            self._reply(STK_INSYNC, STK_OK)
        elif op == CMD_READ_PAGE:
            n = (c[1] << 8) | c[2]
            base = self.here * 2
            src = self.flash if c[3] == ord('F') else self.eeprom
            self._reply(STK_INSYNC)
            self.rx += bytes(src[base:base + n])
            self._reply(STK_OK)
            self.here += n // 2
        else:
            self._reply(STK_NOSYNC)

    def _universal(self, a, b, c, d):
        res = 0
        if (a, b) == (0x50, 0x00):
            res = self.fuses["lfuse"]
        elif (a, b) == (0x58, 0x08):
            res = self.fuses["hfuse"]
        elif (a, b) == (0x50, 0x08):
            res = self.fuses["efuse"]
        elif (a, b) == (0x58, 0x00):
            res = self.lock
        elif (a, b) == (0xAC, 0x80):
            self.flash = bytearray(b"\xFF" * FLASH_SIZE)
            self.lock = 0xFF
        elif (a, b) == (0xAC, 0xA0):
            self.fuses["lfuse"] = d
        elif (a, b) == (0xAC, 0xA8):
            self.fuses["hfuse"] = d
        elif (a, b) == (0xAC, 0xA4):
            self.fuses["efuse"] = d
        elif (a, b) == (0xAC, 0xE0):
            self.lock &= d                      # lock bits can only clear
        self._reply(STK_INSYNC, res, STK_OK)


def selftest(hex_path):
    log("selftest: emulated bricked target behind emulated ArduinoISP\n")
    mock = MockSerial()
    stk = STK500(ser=mock)

    class A:
        check_only = False
        no_backup = True
        erase = False
        fix_fuses = False
        no_lock = False
        hex = hex_path

    recover(stk, A)

    image, lo, hi = parse_intel_hex(hex_path)
    for page in range(lo & ~0x7F, (hi & ~0x7F) + 1, PAGE_SIZE):
        assert bytes(mock.flash[page:page + PAGE_SIZE]) == \
            bytes(image[page:page + PAGE_SIZE]), "flash mismatch @0x%04X" % page
    assert mock.lock == SAFE_LOCK, "lock not set"
    assert mock.fuses == EXPECTED_FUSES, "fuses changed"
    # app area untouched (no erase)
    assert mock.flash[0] == 0xFF and mock.eeprom[0] == 0xAA
    log("\nSELFTEST OK - framing, endianness, page math, fuses, lock all good.")


# --------------------------------------------------------------------------


def find_hex(override):
    if override:
        return override
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (os.getcwd(), here):
        for rel in (r"caterina\Caterina.hex", "Caterina.hex"):
            p = os.path.join(base, rel)
            if os.path.isfile(p):
                return p
    return None


def main():
    ap = argparse.ArgumentParser(description="Pure-python ISP recovery for "
                                     "bricked ATmega32U4 via ArduinoISP")
    ap.add_argument("--port", help="programmer COM port, e.g. COM11")
    ap.add_argument("--baud", type=int, default=19200)
    ap.add_argument("--hex", help="path to Caterina.hex "
                                  "(default: .\\caterina\\Caterina.hex)")
    ap.add_argument("--check-only", action="store_true",
                    help="read signature/fuses only, write nothing")
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--erase", action="store_true",
                    help="full chip erase first (wipes app+eeprom)")
    ap.add_argument("--fix-fuses", action="store_true",
                    help="write fuses if they differ from FF/D8/CB")
    ap.add_argument("--no-lock", action="store_true",
                    help="do not set lock=0x2F (not recommended)")
    ap.add_argument("--lock-only", action="store_true",
                    help="only check/set the lock byte (no flashing)")
    ap.add_argument("--selftest", action="store_true",
                    help="offline protocol test, no hardware needed")
    args = ap.parse_args()

    if args.selftest:
        hex_path = find_hex(args.hex)
        if not hex_path:
            sys.exit("selftest needs Caterina.hex next to this script")
        selftest(hex_path)
        return

    if not args.port:
        ap.error("--port is required (the PROGRAMMER's COM port)")

    if args.lock_only:
        stk = None
        try:
            stk = STK500(port=args.port, baud=args.baud)
            if not stk.sync():
                raise ISPError("no sync with ArduinoISP sketch")
            stk.set_device()
            stk.enter_progmode()
            sig = stk.read_signature()
            if sig != EXPECTED_SIGNATURE:
                raise ISPError("unexpected signature 0x%s" % sig.hex())
            log("signature OK (0x1e9587)")
            ensure_lock(stk, args)
            stk.leave_progmode()
        except ISPError as e:
            log("\nERROR: %s" % e)
            sys.exit(1)
        finally:
            if stk:
                stk.close()
        return

    args.hex = find_hex(args.hex)
    if not args.hex:
        sys.exit("Caterina.hex not found. Run from the _help-from-ai folder "
                 "or pass --hex.")

    stk = None
    try:
        stk = STK500(port=args.port, baud=args.baud)
        recover(stk, args)
    except ISPError as e:
        log("\nERROR: %s" % e)
        sys.exit(1)
    finally:
        if stk:
            stk.close()


if __name__ == "__main__":
    main()
