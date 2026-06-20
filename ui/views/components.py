"""Composants HTML réutilisables pour les vues."""

from __future__ import annotations


def step_icon_html(status: str) -> str:
    if status == "active":
        return (
            '<div style="width:28px;height:28px;border-radius:50%;background:#fff;border:2px solid #F1D9CC;'
            'display:flex;align-items:center;justify-content:center">'
            '<div style="width:15px;height:15px;border-radius:50%;border:2px solid #EAD3C6;'
            'border-top-color:#C2613B;animation:dsSpin .8s linear infinite"></div></div>'
        )
    if status == "done":
        return (
            '<div style="width:28px;height:28px;border-radius:50%;background:#E7F1EC;border:2px solid #CDE6DB;'
            'display:flex;align-items:center;justify-content:center">'
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0F6B54" stroke-width="2.6" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"></path></svg></div>'
        )
    return (
        '<div style="width:28px;height:28px;border-radius:50%;background:#fff;border:2px solid #ECE7D9"></div>'
    )


def render_timeline_html(steps: list[dict]) -> str:
    rows = ['<div class="ds-timeline"><div style="position:relative">', '<div class="ds-timeline-line"></div>']
    for step in steps:
        status = step.get("status", "pending")
        color = "#C2613B" if status == "active" else "#0F6B54" if status == "done" else "#A7AEA8"
        status_text = "En cours…" if status == "active" else "Terminé" if status == "done" else "En attente"
        rows.append(
            f'<div class="ds-step">'
            f'<div style="position:relative;z-index:1;width:28px;flex:none;display:flex;justify-content:center;padding-top:1px">'
            f"{step_icon_html(status)}"
            f"</div>"
            f'<div style="flex:1;min-width:0;padding-top:2px">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:5px">'
            f'<span class="ds-step-tool">{step.get("tool", "")}</span>'
            f'<span style="font:500 11px/1 IBM Plex Sans,sans-serif;color:{color}">{status_text}</span>'
            f"</div>"
            f'<div class="ds-step-title">{step.get("title", "")}</div>'
            f'<div class="ds-step-detail">{step.get("detail", "")}</div>'
            f"</div></div>"
        )
    rows.append("</div></div>")
    return "".join(rows)


def render_sources_html(sources: list[dict], *, count_label: bool = True) -> str:
    header = ""
    if count_label:
        header = (
            f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">'
            f'<span class="ds-section-label" style="margin:0">SOURCES COLLECTÉES</span>'
            f'<span style="font:600 12px/1 Space Grotesk,sans-serif;color:#0F6B54;background:#E9F1ED;'
            f'padding:3px 8px;border-radius:7px">{len(sources)}</span></div>'
        )
    if not sources:
        return header + '<div style="font:400 13px/1.5 IBM Plex Sans,sans-serif;color:#A6AEA7;padding:6px 0 4px">En attente des premiers résultats…</div>'
    items = []
    for src in sources:
        cred_color = src.get("cred_color", "#1F8A5B")
        items.append(
            f'<div style="display:flex;gap:10px;align-items:flex-start;margin-bottom:11px">'
            f'<div style="width:26px;height:26px;border-radius:7px;background:#F2F4F1;display:flex;align-items:center;'
            f'justify-content:center;flex:none;margin-top:1px">🌐</div>'
            f'<div style="flex:1;min-width:0">'
            f'<div style="font:500 13px/1.3 IBM Plex Sans,sans-serif;color:#1F2823;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{src.get("t", "")}</div>'
            f'<div style="display:flex;align-items:center;gap:7px;margin-top:3px">'
            f'<span style="font:400 11px/1 IBM Plex Mono,monospace;color:#9AA39C">{src.get("d", "")}</span>'
            f'<span style="width:3px;height:3px;border-radius:50%;background:#CCD3CC"></span>'
            f'<span style="font:500 10.5px/1 IBM Plex Sans,sans-serif;color:{cred_color}">{src.get("cred", "")}</span>'
            f"</div></div></div>"
        )
    return header + "".join(items)


def render_report_sources_html(sources: list[dict]) -> str:
    items = []
    for i, src in enumerate(sources, 1):
        cred_color = src.get("cred_color", "#1F8A5B")
        items.append(
            f'<div style="display:flex;gap:11px;align-items:flex-start;margin-bottom:13px">'
            f'<span style="width:20px;height:20px;border-radius:6px;background:#F2F4F1;color:#586059;'
            f'font:600 11px/20px Space Grotesk,sans-serif;text-align:center;flex:none">{i}</span>'
            f'<div style="flex:1;min-width:0">'
            f'<div style="font:500 13px/1.3 IBM Plex Sans,sans-serif;color:#1F2823">{src.get("t", src.get("title", ""))}</div>'
            f'<div style="display:flex;align-items:center;gap:7px;margin-top:3px">'
            f'<span style="font:400 11px/1 IBM Plex Mono,monospace;color:#9AA39C">{src.get("d", src.get("domain", ""))}</span>'
            f'<span style="width:3px;height:3px;border-radius:50%;background:#CCD3CC"></span>'
            f'<span style="font:500 10.5px/1 IBM Plex Sans,sans-serif;color:{cred_color}">{src.get("cred", "")}</span>'
            f"</div></div></div>"
        )
    return "".join(items) if items else '<div style="color:#A6AEA7;font-size:13px">Aucune source enregistrée.</div>'
