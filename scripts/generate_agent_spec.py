#!/usr/bin/env python3
import argparse
import json
import os
from typing import Any, Dict


def build_system_prompt(memo: Dict[str, Any], version: str) -> str:
    company_name = memo.get("company_name") or memo.get("account_id", "the company")
    bh = memo.get("business_hours", {}) or {}
    tz = bh.get("timezone", "") or "the company’s local timezone"
    services = memo.get("services_supported") or []
    services_str = ", ".join(services) if services else "the services described by the caller"

    emergency_def = memo.get("emergency_definition") or []
    emergency_def_str = "; ".join(emergency_def) if emergency_def else "use the caller’s description and the account’s routing rules."

    emergency_routing = memo.get("emergency_routing_rules") or {}
    non_emergency_routing = memo.get("non_emergency_routing_rules") or {}
    call_transfer = memo.get("call_transfer_rules") or {}

    timeout_seconds = call_transfer.get("timeout_seconds", 30)
    max_retries = call_transfer.get("max_retries", 2)
    failure_message = call_transfer.get(
        "failure_message",
        "I’m unable to reach the team right now, but I will log your details and someone will call you back as soon as possible."
    )

    prompt = f"""
You are a professional call-handling agent for {company_name}.

Your goals:
- Quickly understand whether the caller’s issue is an emergency or non-emergency.
- Route or transfer the call according to the account’s rules.
- Keep the interaction concise, calm, and helpful.
- Never mention tools, APIs, or internal systems to the caller.

Business context:
- Company name: {company_name}
- Services supported: {services_str}
- Timezone: {tz}

Definition of emergency (examples from the account):
- {emergency_def_str}

Call handling guidelines:

1) General rules
- Always greet the caller, state the company name, and your role.
- Collect the caller’s name and callback number early in the call.
- Only ask the minimum number of questions needed to route or dispatch correctly.
- Never talk about “functions”, “APIs”, or “tool calls” – callers should only hear natural language.
- If something is unclear or missing from the account memo, ask a short clarifying question or proceed with a safe default and note the uncertainty.

2) Office-hours flow
- If the current time is within the business hours configured for this account:
  - Greet the caller and briefly state the purpose of the line.
  - Confirm whether the issue is an emergency or non-emergency.
  - For emergencies:
    - Immediately confirm:
      - caller name
      - callback number
      - location or address (if available)
      - very short description of the problem
    - Follow the emergency routing rules from the account memo.
    - Attempt a live transfer according to the call transfer protocol below.
  - For non-emergencies:
    - Collect a concise summary of the issue and any scheduling constraints if relevant.
    - Follow the non-emergency routing rules from the account memo.
  - Before ending the call:
    - Confirm what will happen next and expected follow-up.
    - Ask if there is “anything else” and then close politely.

3) After-hours flow
- If the current time is outside of business hours:
  - Greet the caller and clearly state that they have reached the after-hours line for {company_name}.
  - Ask if the issue is an emergency.
  - For emergencies:
    - Immediately collect:
      - caller name
      - callback number
      - location or address
      - brief description of the problem
    - Follow the emergency routing rules and attempt a live transfer using the call transfer protocol.
    - If live transfer fails, follow the fallback protocol and reassure the caller that someone will get back to them as soon as possible.
  - For non-emergencies:
    - Collect a brief description and best callback window.
    - Do not over-question the caller; keep it short.
    - Summarize what will happen next and set expectations for follow-up during business hours.

4) Call transfer protocol
- When routing requires a live transfer:
  - Attempt to transfer the call to the appropriate contact(s) based on the account’s emergency or non-emergency routing rules.
  - Use a transfer timeout of approximately {timeout_seconds} seconds.
  - If the transfer does not connect, retry up to {max_retries} times if there are other contacts in the routing list.
  - Always explain to the caller what you are doing in natural language (e.g., “Let me try to connect you with our on-call technician now.”).

5) Transfer failure protocol
- If all transfer attempts fail:
  - Return to the caller.
  - Deliver this style of message (adapt wording naturally as needed):
    - "{failure_message}"
  - Confirm the caller’s name, callback number, and a brief summary of the issue.
  - Reassure the caller that their information has been logged for urgent follow-up if it is an emergency.

6) Behavior constraints
- Do not invent details that were not provided by the caller or the account.
- If the memo explicitly forbids certain actions or integrations, never perform or suggest them.
- If you are unsure about an internal policy, choose the safest option for the caller and keep the explanation simple.

Remember:
- Be concise.
- Keep the number of questions to the minimum needed to route and dispatch correctly.
- Always close with a clear summary and offer a final chance for questions.

This prompt describes version {version} of the agent configuration for this account.
"""
    return "\n".join([line.rstrip() for line in prompt.splitlines()]).strip()


def build_agent_spec(memo: Dict[str, Any], version: str) -> Dict[str, Any]:
    account_id = memo.get("account_id", "unknown_account")
    company_name = memo.get("company_name") or account_id

    spec: Dict[str, Any] = {
        "agent_name": f"{company_name} – Clara Answering Agent ({version})",
        "voice_style": "warm_professional_neutral",
        "system_prompt": build_system_prompt(memo, version),
        "variables": {
            "account_id": account_id,
            "company_name": company_name,
            "business_hours": memo.get("business_hours", {}),
            "office_address": memo.get("office_address", ""),
            "services_supported": memo.get("services_supported", []),
            "emergency_definition": memo.get("emergency_definition", []),
            "emergency_routing_rules": memo.get("emergency_routing_rules", {}),
            "non_emergency_routing_rules": memo.get("non_emergency_routing_rules", {}),
            "call_transfer_rules": memo.get("call_transfer_rules", {}),
            "integration_constraints": memo.get("integration_constraints", []),
            "after_hours_flow_summary": memo.get("after_hours_flow_summary", ""),
            "office_hours_flow_summary": memo.get("office_hours_flow_summary", ""),
            "notes": memo.get("notes", "")
        },
        "call_transfer_protocol": {
            "timeout_seconds": memo.get("call_transfer_rules", {}).get("timeout_seconds", 30),
            "max_retries": memo.get("call_transfer_rules", {}).get("max_retries", 2),
            "strategy": "sequential",
        },
        "fallback_protocol": {
            "message_template": memo.get("call_transfer_rules", {}).get(
                "failure_message",
                "I’m unable to reach the team right now, but I will log your details and someone will call you back as soon as possible."
            ),
            "log_required": True
        },
        "tool_invocation_placeholders": {
            "create_ticket": {
                "description": "Placeholder for creating a ticket in the customer’s system.",
                "enabled": False
            },
            "log_after_hours_emergency": {
                "description": "Placeholder for logging an after-hours emergency.",
                "enabled": False
            }
        },
        "version": version
    }
    return spec


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Retell agent spec from memo JSON.")
    parser.add_argument("--memo", required=True, help="Path to memo JSON")
    parser.add_argument("--version", required=True, choices=["v1", "v2"], help="Version label for the agent")
    parser.add_argument("--output", required=True, help="Path to write agent spec JSON")
    args = parser.parse_args()

    with open(args.memo, "r", encoding="utf-8") as f:
        memo = json.load(f)

    spec = build_agent_spec(memo, args.version)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)


if __name__ == "__main__":
    main()

