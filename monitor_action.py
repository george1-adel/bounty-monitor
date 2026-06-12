"""
Bounty Monitor - GitHub Actions Version
Runs on cron schedule, detects new bug bounty programs/scopes,
sends Telegram notifications to all subscribers.
"""
import requests
import json
import os
import time
import re

# ==================== Configuration ====================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "5789183030:AAElmk-M-SL2BtV4UFXp5A_yslcTG3Q4cxo")
SCAN_BOT_TOKEN     = os.environ.get("SCAN_BOT_TOKEN", "8768326236:AAGnxaF1OVpIXvI5A-098t0kCxEFeYMTGBY")
ADMIN_CHAT_ID      = "1350722553"
GITHUB_TOKEN       = os.environ.get("GH_PAT", "")
GITHUB_REPO_OWNER  = "george1-adel"
GITHUB_REPO_NAME   = "bounty-monitor"

DATA_DIR              = "bounty_data"
SUBSCRIBERS_FILE      = os.path.join(DATA_DIR, "subscribers.json")
PRIVATE_TRACKER_FILE  = os.path.join(DATA_DIR, "private_programs_tracker.json")
TG_OFFSET_FILE        = os.path.join(DATA_DIR, "tg_offset.json")

SOURCES = {
    "HackerOne": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/hackerone_data.json",
    "Bugcrowd":  "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/bugcrowd_data.json",
    "Intigriti": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/intigriti_data.json",
    "YesWeHack": "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/yeswehack_data.json",
    "Federacy":  "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/federacy_data.json",
}

SOURCE_CODE_DOMAINS = {
    "github.com", "gitlab.com", "bitbucket.org", "sourceforge.net",
    "codeberg.org", "play.google.com", "apps.apple.com", "itunes.apple.com",
    "npmjs.com", "pypi.org", "rubygems.org", "hub.docker.com", "crates.io"
}
# =======================================================


# ---------- Subscribers ----------
def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE) as f:
                return set(json.load(f))
        except Exception:
            pass
    return {ADMIN_CHAT_ID}

def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(subs), f)


# ---------- Private tracker ----------
def load_private_tracker():
    if os.path.exists(PRIVATE_TRACKER_FILE):
        try:
            with open(PRIVATE_TRACKER_FILE) as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def save_private_tracker(s):
    with open(PRIVATE_TRACKER_FILE, "w") as f:
        json.dump(list(s), f)


# ---------- Telegram helpers ----------
def send_message(chat_id, text, token=None):
    tok = token or TELEGRAM_BOT_TOKEN
    try:
        requests.post(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            json={"chat_id": chat_id, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10
        )
    except Exception as e:
        print(f"  Telegram error -> {chat_id}: {e}")

def broadcast(text):
    subs = load_subscribers()
    ok = 0
    for chat_id in subs:
        send_message(chat_id, text)
        ok += 1
        time.sleep(0.3)
    print(f"  Broadcast: {ok}/{len(subs)} subscribers")


# ---------- Handle /start from Monitor bot ----------
def handle_telegram_updates():
    """Poll Telegram once and process any /start commands."""
    offset = 0
    if os.path.exists(TG_OFFSET_FILE):
        try:
            with open(TG_OFFSET_FILE) as f:
                offset = json.load(f).get("offset", 0)
        except Exception:
            pass

    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
            params={"offset": offset, "timeout": 5},
            timeout=15
        )
        data = resp.json()
    except Exception as e:
        print(f"  Telegram poll error: {e}")
        return

    subs = load_subscribers()
    changed = False

    for result in data.get("result", []):
        offset = result["update_id"] + 1
        msg    = result.get("message", {})
        chat_id = str(msg.get("chat", {}).get("id", ""))
        text    = msg.get("text", "").strip()

        if not chat_id or not text:
            continue

        if text == "/start":
            if chat_id not in subs:
                subs.add(chat_id)
                changed = True
                send_message(chat_id, (
                    "👋 <b>Welcome to the Bug Bounty Monitor Bot!</b>\n\n"
                    "🔍 I monitor top platforms every <b>15 minutes</b> and notify you when:\n"
                    "• 🚀 A new public program is launched\n"
                    "• 🔓 A private program goes public\n"
                    "• 🎯 New scopes are added to existing programs\n\n"
                    "<b>Platforms:</b> HackerOne · Bugcrowd · Intigriti · YesWeHack · Federacy\n\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "👋 <b>أهلاً بك في بوت مراقبة Bug Bounty!</b>\n\n"
                    "🔍 أراقب المنصات كل <b>15 دقيقة</b> وأُخطرك فوراً عند:\n"
                    "• 🚀 إطلاق برنامج جديد\n"
                    "• 🔓 تحويل برنامج خاص إلى عام\n"
                    "• 🎯 إضافة نطاقات (Scopes) جديدة"
                ))
                print(f"  New subscriber: {chat_id}")
            else:
                send_message(chat_id, "✅ أنت مشترك بالفعل وتتلقى التحديثات!")

        elif text == "/stop":
            if chat_id in subs and chat_id != ADMIN_CHAT_ID:
                subs.discard(chat_id)
                changed = True
                send_message(chat_id, "👋 تم إلغاء اشتراكك. أرسل /start للاشتراك مجدداً.")

        elif text == "/stats" and chat_id == ADMIN_CHAT_ID:
            send_message(chat_id, f"📊 <b>Bot Stats</b>\n\n👥 Subscribers: <b>{len(subs)}</b>")

    if changed:
        save_subscribers(subs)

    with open(TG_OFFSET_FILE, "w") as f:
        json.dump({"offset": offset}, f)


# ---------- Scope helpers ----------
def is_scannable_scope(scope):
    scope_lower = scope.strip().lower()
    for blocked in SOURCE_CODE_DOMAINS:
        if blocked in scope_lower:
            return False
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', scope_lower):
        return False
    return True

def trigger_github_action(domain):
    if not is_scannable_scope(domain) or not GITHUB_TOKEN:
        return
    url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/dispatches"
    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"token {GITHUB_TOKEN}",
                     "Accept": "application/vnd.github.v3+json"},
            json={"event_type": "new_scope_event",
                  "client_payload": {"domain": domain, "source": "auto"}},
            timeout=10
        )
        if resp.status_code == 204:
            print(f"  [+] Scan triggered: {domain}")
    except Exception as e:
        print(f"  [!] Trigger error for {domain}: {e}")

def get_identifier(target):
    if isinstance(target, dict):
        return (target.get("asset_identifier") or
                target.get("target") or
                target.get("endpoint") or str(target))
    return str(target)


# ---------- Core monitor ----------
def analyze_platform(platform_name, url):
    print(f"\n[*] Checking {platform_name}...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        current_list = response.json()
    except Exception as e:
        print(f"  [!] Fetch error: {e}")
        return

    current_data = {}
    for p in current_list:
        key = p.get("url") or p.get("handle") or p.get("name")
        current_data[key] = p

    filepath = os.path.join(DATA_DIR, f"{platform_name.lower()}.json")

    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(current_data, f)
        print(f"  [+] Initial data saved ({len(current_data)} programs)")
        return

    with open(filepath, encoding="utf-8") as f:
        try:
            old_data = json.load(f)
        except json.JSONDecodeError:
            old_data = {}

    # Update private tracker
    private_tracker = load_private_tracker()
    for p_url, prog in current_data.items():
        conf   = (prog.get("confidentiality_level") or "").lower()
        status = (prog.get("status") or "").lower()
        if conf in ("private", "invitation_only") or status in ("private", "invitation_only"):
            private_tracker.add(p_url)

    new_programs = 0
    new_scopes   = 0

    for p_url, program in current_data.items():
        name    = program.get("name", "Unknown")
        app_url = program.get("url", p_url)
        conf    = (program.get("confidentiality_level") or "").lower()

        # Build current scopes
        current_scopes = []
        targets = program.get("targets", {})
        if isinstance(targets, dict) and "in_scope" in targets:
            for t in targets["in_scope"]:
                current_scopes.append(get_identifier(t))
        elif isinstance(targets, list):
            for t in targets:
                current_scopes.append(get_identifier(t))

        # ---- NEW PROGRAM ----
        if p_url not in old_data:
            new_programs += 1
            scopes_text = "\n".join([f"• <code>{s}</code>" for s in current_scopes[:15]])
            if len(current_scopes) > 15:
                scopes_text += f"\n... and {len(current_scopes)-15} more"

            min_b = program.get("min_bounty") or {}
            max_b = program.get("max_bounty") or {}
            bounty_str = ""
            if isinstance(min_b, dict) and min_b.get("value"):
                bounty_str = f"\n💰 <b>Bounty:</b> ${min_b['value']:,}"
                if isinstance(max_b, dict) and max_b.get("value"):
                    bounty_str += f" – ${max_b['value']:,} {min_b.get('currency','USD')}"

            was_private = (p_url in private_tracker) or (conf in ("private", "invitation_only"))
            if was_private:
                header = f"🔓 <b>Program Went Public!</b>  |  {platform_name}"
                sub    = "\n<i>⚠️ كان برنامج خاص وفتح للعامة الآن</i>"
            else:
                header = f"🚀 <b>New Bug Bounty Program!</b>  |  {platform_name}"
                sub    = ""

            msg = (
                f"{header}{sub}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📌 <b>{name}</b>\n"
                f"🔗 {app_url}{bounty_str}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📂 <b>Scopes ({len(current_scopes)}):</b>\n{scopes_text}"
            )
            broadcast(msg)
            for scope in current_scopes:
                trigger_github_action(scope)
                time.sleep(0.3)
            time.sleep(1)

        # ---- EXISTING PROGRAM — check new scopes ----
        else:
            old_program = old_data[p_url]
            old_scopes  = []
            old_targets = old_program.get("targets", {})
            if isinstance(old_targets, dict) and "in_scope" in old_targets:
                for t in old_targets["in_scope"]:
                    old_scopes.append(get_identifier(t))
            elif isinstance(old_targets, list):
                for t in old_targets:
                    old_scopes.append(get_identifier(t))

            added = set(current_scopes) - set(old_scopes)
            if added:
                new_scopes += 1
                scopes_text = "\n".join([f"• <code>{s}</code>" for s in list(added)[:15]])
                if len(added) > 15:
                    scopes_text += f"\n... and {len(added)-15} more"

                msg = (
                    f"🎯 <b>New Scope Added</b>  |  {platform_name}\n"
                    f"──────────────────\n"
                    f"📌 <b>Program:</b> {name}\n"
                    f"🔗 {app_url}\n"
                    f"──────────────────\n"
                    f"✅ <b>New Scopes ({len(added)}):</b>\n{scopes_text}"
                )
                broadcast(msg)
                for scope in added:
                    trigger_github_action(scope)
                    time.sleep(0.3)
                time.sleep(1)

    save_private_tracker(private_tracker)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(current_data, f)

    print(f"  [*] Done. {new_programs} new programs, {new_scopes} with new scopes.")


# ---------- Main ----------
def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print("=== Bounty Monitor — GitHub Actions ===")

    # 1. Handle Telegram /start subscriptions
    handle_telegram_updates()

    # 2. Check all platforms
    for platform_name, url in SOURCES.items():
        analyze_platform(platform_name, url)

    print("\n=== Done ===")

if __name__ == "__main__":
    main()
