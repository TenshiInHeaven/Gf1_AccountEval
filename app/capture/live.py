"""One-shot live account extraction from the PC client via XLua.

The game exposes its Lua runtime through ``xlua.dll``.  We attach with Frida,
hook ``XLua.LuaEnv.Tick`` once, execute a read-only Lua script and return a
tab-separated snapshot.  Nothing is written into the game.
"""
from __future__ import annotations

import datetime as dt
import subprocess
import sys
import tempfile
from pathlib import Path

from ..core.paths import PROJECT_ROOT

LUA_EVAL = Path(__file__).with_name("lua_eval.py")
CACHE_DIR = PROJECT_ROOT / ".cache" / "capture"


LUA_SCRIPT = r"""
local out = {}
local function add(line) out[#out + 1] = line end
local function v(fn)
  local ok, value = pcall(fn)
  if ok then return tostring(value) end
  return ""
end
local function get(fn)
  local ok, value = pcall(fn)
  if ok then return value end
  return nil
end
local function header(text) add(text) end

local u = get(function() return CS.GameData.userInfo end)
add("@@META")
header("userId\tname\tlevel\tmaxGun\tmaxSangvisGun\tmaxFairy\tmaxEquip")
if u ~= nil then
  add(table.concat({
    v(function() return u.userId end),
    v(function() return u.name end),
    v(function() return u.level end),
    v(function() return u.maxGun end),
    v(function() return u.maxSangvisGun end),
    v(function() return u.maxFairy end),
    v(function() return u.maxEquip end),
  }, "\t"))
end

add("@@ROSTER")
header("uid\tcode\tlevel\texp\tfavor\tteamId\tskinId\tlocation\tnumber\tmod")
local guns = get(function() return CS.GameData.listGun end)
if guns ~= nil then
  for i = 0, guns.Count - 1 do
    local g = guns[i]
    if g ~= nil then
      add(table.concat({
        v(function() return g.id end),
        v(function() return g.code end),
        v(function() return g.level end),
        v(function() return g.experience end),
        v(function() return g.favor end),
        v(function() return g.teamId end),
        v(function() return g.currentSkinId end),
        v(function() return g.location end),
        v(function() return g.number end),
        v(function() return g.mod end),
      }, "\t"))
    end
  end
end

add("@@FAIRIES")
header("id\tcode\tlevel\texp\tqualityLevel\tmainSkillLevel\tmod\tmodExp\tteamId\tequipId\tisCollect")
local fairies = get(function() return CS.GameData.listFairy end)
if fairies ~= nil then
  for i = 0, fairies.Count - 1 do
    local f = fairies[i]
    if f ~= nil then
      add(table.concat({
        v(function() return f.id end),
        v(function() return f:GetCode() end),
        v(function() return f.level end),
        v(function() return f.exp end),
        v(function() return f.qualityLevel end),
        v(function() return f.mainSkillLevel end),
        v(function() return f.mod end),
        v(function() return f.modExp end),
        v(function() return f.teamId end),
        v(function() return f.equipId end),
        v(function() return f.isCollect end),
      }, "\t"))
    end
  end
end

add("@@EQUIPMENT")
header("id\tgunId\tinfoId\townNumber\tequip_level\tequip_exp")
local equips = get(function() return CS.GameData.listEquip end)
if equips ~= nil then
  for i = 0, equips.Count - 1 do
    local e = equips[i]
    if e ~= nil then
      add(table.concat({
        v(function() return e.id end),
        v(function() return e.gunId end),
        v(function() return e.info.id end),
        v(function() return e.ownNumber end),
        v(function() return e.equip_level end),
        v(function() return e.equip_exp end),
      }, "\t"))
    end
  end
end

add("@@SANGVIS")
header("infoId\tcode\tlevel\tadvance\tresolutionLevel\tsign\tskin\tbreakThroughLevel\tchip1\tchip2")
local sangvis = get(function() return CS.GameData.listSangvisGun end)
if sangvis ~= nil then
  for i = 0, sangvis.Count - 1 do
    local s = sangvis[i]
    if s ~= nil then
      add(table.concat({
        v(function() return s.infoId end),
        v(function() return s:GetCode() end),
        v(function() return s.level end),
        v(function() return s.advance end),
        v(function() return s.resolutionLevel end),
        v(function() return s.sign end),
        v(function() return s.skin end),
        v(function() return s.breakThroughLevel end),
        v(function() return s.chip1 end),
        v(function() return s.chip2 end),
      }, "\t"))
    end
  end
end

add("@@VEHICLES")
header("id\tinfoid\texp\tlife")
local vehicles = get(function() return CS.GameData.listVehicle end)
if vehicles ~= nil then
  for i = 0, vehicles.Count - 1 do
    local item = vehicles[i]
    if item ~= nil then
      add(table.concat({
        v(function() return item.id end),
        v(function() return item.infoid end),
        v(function() return item.exp end),
        v(function() return item.life end),
      }, "\t"))
    end
  end
end
return table.concat(out, "\n")
"""


class CaptureError(RuntimeError):
    pass


def find_game_pid() -> int | None:
    try:
        import frida
    except Exception as exc:
        raise CaptureError(f"未安装 frida：{exc}") from exc
    device = frida.get_local_device()
    for process in device.enumerate_processes():
        name = (process.name or "").lower()
        if name in {"grilsfrontline.exe", "girlsfrontline.exe"}:
            return int(process.pid)
    return None


def capture(pid: int | None = None, timeout: int = 35) -> tuple[dict, str]:
    try:
        import frida  # noqa: F401
    except Exception as exc:
        raise CaptureError(f"未安装 frida：{exc}") from exc
    pid = pid or find_game_pid()
    if not pid:
        raise CaptureError("没有找到运行中的 GrilsFrontLine.exe，请先启动并登录游戏。")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gf_capture_") as tmp:
        tmp_dir = Path(tmp)
        script_path = tmp_dir / "capture.lua"
        out_path = tmp_dir / "capture.tsv"
        script_path.write_text(LUA_SCRIPT, encoding="utf-8")
        command = [
            sys.executable,
            str(LUA_EVAL),
            "--pid",
            str(pid),
            "--script",
            str(script_path),
            "--out",
            str(out_path),
            "--seconds",
            str(timeout),
        ]
        try:
            proc = subprocess.run(
                command,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout + 15,
            )
        except subprocess.TimeoutExpired as exc:
            raise CaptureError("XLua 提取超时；请确认游戏已进入主界面后重试。") from exc
        if proc.returncode != 0:
            raise CaptureError(f"XLua 提取失败：{proc.stderr.strip() or proc.stdout.strip()}")
        if not out_path.is_file() or out_path.stat().st_size == 0:
            raise CaptureError(f"游戏没有返回数据：{proc.stdout.strip()[-500:]}")
        text = out_path.read_text(encoding="utf-8", errors="replace")
    parsed = parse_capture(text)
    meta = parsed.get("meta") or {}
    unit_count = sum(
        len(parsed.get(key) or [])
        for key in ("dolls", "fairies", "sangvis", "equipment", "vehicles")
    )
    if not str(meta.get("uid") or "").strip() or unit_count == 0:
        raise CaptureError(
            "XLua 已连接，但没有读到账号数据：请确认游戏已进入主界面并保持在前台，"
            "然后重试；如果仍为空，说明当前客户端版本的 LuaEnv hook 未触发，"
            "请先使用「导入快照」。"
        )
    return parsed, text


def parse_capture(text: str) -> dict:
    sections: dict[str, list[dict]] = {}
    current = ""
    header: list[str] | None = None
    for line in text.splitlines():
        line = line.rstrip("\r")
        if not line:
            continue
        if line.startswith("@@"):
            current = line[2:].strip().upper()
            sections[current] = []
            header = None
            continue
        if not current:
            continue
        cells = line.split("\t")
        if header is None:
            header = cells
            continue
        sections[current].append(dict(zip(header, cells)))

    meta_row = (sections.get("META") or [{}])[0]
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    meta = {
        "uid": meta_row.get("userId", ""),
        "nickname": meta_row.get("name", ""),
        "level": meta_row.get("level", ""),
        "max_gun": meta_row.get("maxGun", ""),
        "max_sangvis": meta_row.get("maxSangvisGun", ""),
        "max_fairy": meta_row.get("maxFairy", ""),
        "max_equip": meta_row.get("maxEquip", ""),
        "source": "XLua 实时提取",
        "captured_at": now,
        "game": "少女前线 PC（国服）",
        "note": "只读提取；关闭游戏前建议保留一份快照。",
    }
    return {
        "schema": 1,
        "meta": meta,
        "dolls": [
            {
                "uid": row.get("uid"),
                "code": row.get("code"),
                "level": row.get("level"),
                "exp": row.get("exp"),
                "favor": row.get("favor"),
                "team_id": row.get("teamId"),
                "skin_id": row.get("skinId"),
                "location": row.get("location"),
                "number": row.get("number"),
                "mod": row.get("mod"),
            }
            for row in sections.get("ROSTER", [])
        ],
        "fairies": [
            {
                "id": row.get("id"),
                "code": row.get("code"),
                "level": row.get("level"),
                "exp": row.get("exp"),
                "quality": row.get("qualityLevel"),
                "skill_level": row.get("mainSkillLevel"),
                "mod": row.get("mod"),
                "team_id": row.get("teamId"),
                "equip_id": row.get("equipId"),
                "is_collect": str(row.get("isCollect", "")).lower() == "true",
            }
            for row in sections.get("FAIRIES", [])
        ],
        "equipment": [
            {
                "id": row.get("id"),
                "gun_id": row.get("gunId"),
                "info_id": row.get("infoId"),
                "own_number": row.get("ownNumber"),
                "level": row.get("equip_level"),
                "exp": row.get("equip_exp"),
            }
            for row in sections.get("EQUIPMENT", [])
        ],
        "sangvis": [
            {
                "info_id": row.get("infoId"),
                "code": row.get("code"),
                "level": row.get("level"),
                "advance": row.get("advance"),
                "resolution_level": row.get("resolutionLevel"),
                "sign": row.get("sign"),
                "skin": row.get("skin"),
                "break_through": row.get("breakThroughLevel"),
                "chip1": row.get("chip1"),
                "chip2": row.get("chip2"),
            }
            for row in sections.get("SANGVIS", [])
        ],
        "vehicles": [
            {
                "id": row.get("id"),
                "infoid": row.get("infoid"),
                "exp": row.get("exp"),
                "life": row.get("life"),
            }
            for row in sections.get("VEHICLES", [])
        ],
        "teams": [],
        "squads": [],
    }
