"""XLua 执行器：在 LuaEnv.Tick 主线程上跑一段 Lua，取返回值写文件。

利用 xlua.dll 导出的 Lua C API（luaL_loadstring/lua_pcall/lua_tolstring），
不依赖游戏 C# 封装；一次 Tick 执行后立即 detach。

用法：
  python tools\\gfl_pc_export\\hooks\\lua_eval.py --pid 76744 --script tmp\\lua_hello.lua --out tmp\\lua_result.txt
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import frida

ROOT = Path(__file__).resolve().parents[1]

JS = r"""
(function () {
  const SCRIPT = __SCRIPT__;
  const OUT = "__OUT__";
  const EVENT_OUT = OUT + ".events";
  function emit(kind, data) {
    try { send({event: kind, data: data}); } catch (e) {}
    try {
      const f = new File(EVENT_OUT, "a");
      f.write(JSON.stringify({t: Date.now(), event: kind, data: data}) + "\n");
      f.flush();
    } catch (e) {}
  }
  function rs(p) { try { return p.isNull() ? "" : p.readUtf8String(); } catch (e) { return ""; } }
  function klassName(a) { try { return rs(a.readPointer().add(0x10).readPointer()); } catch (e) { return ""; } }

  const mod = Process.getModuleByName("xlua.dll");
  const load = new NativeFunction(mod.getExportByName("luaL_loadstring"), "int", ["pointer", "pointer"]);
  const pcall = new NativeFunction(mod.getExportByName("lua_pcall"), "int",
                                   ["pointer", "int", "int", "int"]);
  const tolstring = new NativeFunction(mod.getExportByName("lua_tolstring"), "pointer",
                                        ["pointer", "int", "pointer"]);
  const settop = new NativeFunction(mod.getExportByName("lua_settop"), "void", ["pointer", "int"]);

  const up = Process.getModuleByName("UnityPlayer.dll");
  const table = up.base.add(0x15cd9e0);
  function api(i) { return table.add(i * Process.pointerSize).readPointer(); }
  const dg = new NativeFunction(api(70), 'pointer', []);
  const ga = new NativeFunction(api(72), 'pointer', ['pointer', 'pointer']);
  const agi = new NativeFunction(api(24), 'pointer', ['pointer']);
  const cc = new NativeFunction(api(179), 'uint32', ['pointer']);
  const gc = new NativeFunction(api(180), 'pointer', ['pointer', 'uint32']);
  const gn = new NativeFunction(api(44), 'pointer', ['pointer']);
  const gm = new NativeFunction(api(42), 'pointer', ['pointer', 'pointer']);
  const domain = dg();
  const sp = Memory.alloc(8);
  const asms = ga(domain, sp);
  const n = sp.readU64().toNumber();
  let luaEnvClass = null;
  for (let i = 0; i < n && !luaEnvClass; i++) {
    let img; try { img = agi(asms.add(i * Process.pointerSize).readPointer()); } catch (e) { continue; }
    let cnt = 0; try { cnt = cc(img); } catch (e) { continue; }
    for (let j = 0; j < cnt; j++) {
      let k; try { k = gc(img, j); } catch (e) { continue; }
      if (!k || k.isNull()) continue;
      if (rs(gn(k)) === "LuaEnv") { luaEnvClass = k; break; }
    }
  }
  if (!luaEnvClass) { emit("error", {message: "LuaEnv not found"}); return; }

  let done = false;
  let tickPtr = null;
  try {
    const it = Memory.alloc(8); it.writePointer(ptr(0));
    for (let q = 0; q < 64; q++) {
      let m; try { m = gm(luaEnvClass, it); } catch (e) { break; }
      if (!m || m.isNull()) break;
      let mn = ""; try { mn = m.add(16).readPointer().readUtf8String(); } catch (e) {}
      if (mn === "Tick") { tickPtr = m.readPointer(); break; }
    }
  } catch (e) {}
  if (!tickPtr) { emit("error", {message: "LuaEnv.Tick not found"}); return; }

  Interceptor.attach(tickPtr, {
    onEnter(args) {
      if (done) return;
      if (klassName(args[0]) !== "LuaEnv") return;
      done = true;
      try {
        const L = args[0].add(16).readPointer();
        if (!L || L.isNull()) { emit("error", {message: "rawL null"}); return; }
        const scriptPtr = Memory.allocUtf8String(SCRIPT);
        const loadRet = load(L, scriptPtr);
        if (loadRet !== 0) {
          const lenPtr = Memory.alloc(8);
          const p = tolstring(L, -1, lenPtr);
          emit("error", {message: "load failed", ret: loadRet, text: rs(p)});
          try { settop(L, 0); } catch (e) {}
          return;
        }
        const pcallRet = pcall(L, 0, 1, 0);
        const lenPtr = Memory.alloc(8);
        const p = tolstring(L, -1, lenPtr);
        const text = rs(p);
        emit("result", {pcall: pcallRet, text: text});
        try { settop(L, 0); } catch (e) {}
      } catch (e) {
        emit("error", {message: String(e)});
      } finally {
        try { Interceptor.detachAll(); } catch (e) {}
      }
    }
  });
  emit("ready", {});
})();
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--script", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seconds", type=int, default=60)
    args = ap.parse_args()
    script_text = args.script.read_text(encoding="utf-8")
    args.out.write_text("", encoding="utf-8")
    js = JS.replace("__SCRIPT__", json.dumps(script_text)).replace(
        "__OUT__", str(args.out).replace("\\", "\\\\"))
    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("", encoding="utf-8")
    def on_message(m, d):
        payload = m.get("payload", m)
        if isinstance(payload, dict) and payload.get("event") == "result":
            text = (payload.get("data") or {}).get("text", "")
            out_path.write_text(text, encoding="utf-8")
            print("result chars:", len(text), flush=True)
        else:
            print(payload, flush=True)
    session = frida.attach(args.pid)
    script = session.create_script(js)
    script.on("message", on_message)
    script.load()
    print(f"lua eval ready; script={args.script}", flush=True)
    # The hook usually runs on the next frame.  Poll the result file so we can
    # detach as soon as data arrives instead of sleeping for the full timeout.
    for _ in range(max(1, args.seconds * 10)):
        if out_path.stat().st_size > 0:
            time.sleep(0.2)
            break
        time.sleep(0.1)
    session.detach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
