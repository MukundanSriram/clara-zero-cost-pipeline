#!/usr/bin/env python3
import argparse
import json
import os
import re
from typing import Any, Dict, List, Optional


def _normalize_line(line: str) -> str:
    return line.strip().lower()


def _find_company_name(lines: List[str]) -> Optional[str]:
    # Simple heuristic: look for "this is <company>" or "from <company>"
    for line in lines[:40]:
        m = re.search(r"(?:this is|you're calling|you are calling|from)\s+([^.,]+)", line, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def _extract_business_hours(text: str) -> Dict[str, Any]:
    # Default conservative empty structure
    result: Dict[str, Any] = {
        "days": [],
        "start": "",
        "end": "",
        "timezone": ""
    }

    # Days of week
    days_map = {
        "monday": "Mon",
        "tuesday": "Tue",
        "wednesday": "Wed",
        "thursday": "Thu",
        "friday": "Fri",
        "saturday": "Sat",
        "sunday": "Sun",
        "mon": "Mon",
        "tue": "Tue",
        "wed": "Wed",
        "thu": "Thu",
        "fri": "Fri",
        "sat": "Sat",
        "sun": "Sun",
    }
    found_days: List[str] = []
    for word, short in days_map.items():
        if re.search(rf"\b{word}s?\b", text, re.IGNORECASE):
            if short not in found_days:
                found_days.append(short)
    if found_days:
        result["days"] = found_days

    # Times like 8am, 8:00 am, 17:00, etc.
    time_matches = re.findall(r"(\d{1,2}(:\d{2})?\s*(am|pm)?)", text, re.IGNORECASE)
    if len(time_matches) >= 2:
        def _to_24h(raw: str) -> str:
            raw = raw.strip()
            try:
                # crude normalization
                m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", raw, re.IGNORECASE)
                if not m:
                    return ""
                hour = int(m.group(1))
                minute = int(m.group(2)) if m.group(2) else 0
                ampm = m.group(3).lower() if m.group(3) else ""
                if ampm == "pm" and hour != 12:
                    hour += 12
                if ampm == "am" and hour == 12:
                    hour = 0
                return f"{hour:02d}:{minute:02d}"
            except Exception:
                return ""

        start_raw = time_matches[0][0]
        end_raw = time_matches[1][0]
        result["start"] = _to_24h(start_raw)
        result["end"] = _to_24h(end_raw)

    # Timezone
    tz_patterns = [
        ("pacific", "America/Los_Angeles"),
        ("eastern", "America/New_York"),
        ("central", "America/Chicago"),
        ("mountain", "America/Denver"),
    ]
    for key, tz in tz_patterns:
        if key in text.lower():
            result["timezone"] = tz
            break

    return result


def _extract_services(lines: List[str]) -> List[str]:
    services: List[str] = []
    keywords = [
        "sprinkler", "alarm", "monitoring", "inspection", "repair",
        "maintenance", "testing", "backflow", "fire pump", "security"
    ]
    for line in lines:
        for kw in keywords:
            if kw in line.lower() and kw not in services:
                services.append(kw)
    return services


def _extract_address(text: str) -> str:
    # Very rough heuristic: look for something that looks like street number + street
    m = re.search(r"\b\d{2,5}\s+[^,\n]+,\s*[^,\n]+,\s*[A-Z]{2}\s*\d{5}\b", text)
    if m:
        return m.group(0).strip()
    return ""


def _extract_emergency_definitions(lines: List[str]) -> List[str]:
    triggers: List[str] = []
    for line in lines:
        low = line.lower()
        if "emergency" in low:
            cleaned = line.strip()
            if cleaned and cleaned not in triggers:
                triggers.append(cleaned)
    return triggers


def _extract_routing_rules(lines: List[str]) -> Dict[str, Any]:
    emergency = {"primary": [], "fallback": [], "notes": ""}
    non_emergency = {"primary": [], "fallback": [], "notes": ""}

    for line in lines:
        low = line.lower()
        if "on-call" in low or "on call" in low:
            if "emergency" in low:
                if "on_call_technician" not in emergency["primary"]:
                    emergency["primary"].append("on_call_technician")
        if "branch manager" in low or "manager" in low:
            if "branch_manager" not in emergency["fallback"]:
                emergency["fallback"].append("branch_manager")
        if "front desk" in low or "reception" in low:
            if "front_desk" not in non_emergency["primary"]:
                non_emergency["primary"].append("front_desk")

    return {"emergency": emergency, "non_emergency": non_emergency}


def _extract_integration_constraints(lines: List[str]) -> List[str]:
    constraints: List[str] = []
    for line in lines:
        low = line.lower()
        if "never" in low or "do not" in low or "don't" in low:
            constraints.append(line.strip())
    return constraints


def extract_account_memo(account_id: str, transcript: str) -> Dict[str, Any]:
    lines = [l.strip() for l in transcript.splitlines() if l.strip()]
    lower_lines = [_normalize_line(l) for l in lines]
    full_text = "\n".join(lines)

    questions_or_unknowns: List[str] = []

    company_name = _find_company_name(lines)
    if not company_name:
        questions_or_unknowns.append("Company name not clearly stated.")

    business_hours = _extract_business_hours(full_text)
    if not business_hours["days"] or not business_hours["start"] or not business_hours["end"]:
        questions_or_unknowns.append("Business hours incomplete or missing.")

    office_address = _extract_address(full_text)
    if not office_address:
        questions_or_unknowns.append("Office address missing.")

    services_supported = _extract_services(lines)
    if not services_supported:
        questions_or_unknowns.append("Services supported not clearly listed.")

    emergency_definition = _extract_emergency_definitions(lines)
    if not emergency_definition:
        questions_or_unknowns.append("Emergency definition unclear.")

    routing = _extract_routing_rules(lines)
    integration_constraints = _extract_integration_constraints(lines)

    memo: Dict[str, Any] = {
        "account_id": account_id,
        "company_name": company_name or "",
        "business_hours": business_hours,
        "office_address": office_address,
        "services_supported": services_supported,
        "emergency_definition": emergency_definition,
        "emergency_routing_rules": routing["emergency"],
        "non_emergency_routing_rules": routing["non_emergency"],
        "call_transfer_rules": {
            "timeout_seconds": 30,
            "max_retries": 2,
            "failure_message": "I’m unable to reach the on-call team right now, but I will log your details and someone will call you back as soon as possible."
        },
        "integration_constraints": integration_constraints,
        "after_hours_flow_summary": "",
        "office_hours_flow_summary": "",
        "questions_or_unknowns": questions_or_unknowns,
        "notes": ""
    }
    return memo


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract structured account memo from a transcript.")
    parser.add_argument("--input", required=True, help="Path to transcript .txt file")
    parser.add_argument("--account-id", required=False, help="Account ID (defaults from filename prefix)")
    parser.add_argument("--output", required=True, help="Path to write memo JSON")
    args = parser.parse_args()

    input_path = args.input
    with open(input_path, "r", encoding="utf-8") as f:
        transcript = f.read()

    account_id = args.account_id
    if not account_id:
        basename = os.path.basename(input_path)
        # e.g. acme_demo_1.txt -> acme
        account_id = re.split(r"_demo|_onboarding", basename, maxsplit=1)[0]

    memo = extract_account_memo(account_id, transcript)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(memo, f, indent=2)


if __name__ == "__main__":
    main()

