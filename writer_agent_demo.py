from __future__ import annotations

import asyncio
from pprint import pprint

from core.groupagents.mega_agent import (CommandType, MegaAgent,
                                         MegaAgentCommand)


async def main() -> None:
    agent = MegaAgent()

    letter_payload = {
        "content_data": {
            "recipient": "Jane Doe",
            "content": "We are pleased to confirm your upcoming consultation on October 12.",
            "closing": "Sincerely",
            "sender": "Mega Agent Pro",
            "subject": "Consultation Confirmation",
            "sender_name": "Mega Agent Pro",
            "sender_title": "Client Success",
            "sender_contact": "contact@mega-agent.pro",
            "recipient_address": "123 Main St, Springfield",
            "recipient_name": "Jane Doe",
            "closing_phrase": "Please reach out if you need to reschedule.",
            "date": "2025-09-16",
        },
        "tone": "formal",
        "language": "en",
        "case_id": "case-demo-001",
    }

    generate_command = MegaAgentCommand(
        user_id="writer-demo",
        command_type=CommandType.GENERATE,
        action="letter",
        payload=letter_payload,
    )
    letter_response = await agent.handle_command(generate_command)
    print("=== Letter Generated ===")
    print("success:", letter_response.success)
    print("error:", letter_response.error)
    pprint(letter_response.result)

    if not letter_response.success:
        return

    document_id = letter_response.result.get("document_id")
    pdf_command = MegaAgentCommand(
        user_id="writer-demo",
        command_type=CommandType.GENERATE,
        action="generate_pdf",
        payload={"document_id": document_id},
    )
    pdf_response = await agent.handle_command(pdf_command)
    print("\n=== PDF Generated ===")
    print("success:", pdf_response.success)
    print("error:", pdf_response.error)
    pprint(pdf_response.result)

    get_command = MegaAgentCommand(
        user_id="writer-demo",
        command_type=CommandType.GENERATE,
        action="get",
        payload={"document_id": document_id},
    )
    get_response = await agent.handle_command(get_command)
    print("\n=== Document Retrieved ===")
    print("success:", get_response.success)
    print("error:", get_response.error)
    pprint(get_response.result)


if __name__ == "__main__":
    asyncio.run(main())
