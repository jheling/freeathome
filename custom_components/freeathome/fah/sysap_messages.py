"""Find notifications of the SysAP that Home Assistant has not reported yet.

The SysAP keeps its notifications under <messages> in getAll. On 27.09.2026 a
fire alarm left this entry:

    <message i="0" topic="system.notification" nameId="05C4"
             time="20260927201602008" severity="high">Wohnzimmer</message>

It names the room of the triggering detector. All networked detectors turn on
in the same second in Home Assistant, so the entities cannot tell which one
saw the smoke.

Kept free of slixmpp and Home Assistant imports, so it can be tested alone.
"""
from datetime import datetime, timezone


def _message_time(raw):
    """Turn 20260927201602008 (UTC, milliseconds) into an ISO timestamp."""
    try:
        moment = datetime.strptime(raw[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None
    return moment.isoformat()


def new_messages(root, seen):
    """Return every message below root that is not in seen, and add it to seen.

    root: parsed XML of an update or of getAll (both carry <messages>).
    seen: set shared across reconnects, so a reconnect does not repeat old
    messages. It only grows by the few notifications the SysAP keeps.
    """
    result = []
    if root is None:
        return result
    for message in root.findall("messages/message"):
        text = (message.text or "").strip()
        key = (message.get("topic"), message.get("time"), text)
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "topic": message.get("topic"),
            "name_id": message.get("nameId"),
            "title": message.get("title"),
            "text": text,
            "severity": message.get("severity"),
            "logic_id": message.get("logicId"),
            "time": _message_time(message.get("time")),
        })
    return result
