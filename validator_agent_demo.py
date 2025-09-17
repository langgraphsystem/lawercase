import asyncio
from pprint import pprint

from core.groupagents.mega_agent import CommandType, MegaAgent, MegaAgentCommand


def print_section(title: str) -> None:
    print(f"\n=== {title} ===")


async def main() -> None:
    agent = MegaAgent()

    # Document validation with issues
    doc_payload = {
        "validation_type": "document",
        "data": {
            "title": "Doc",
            "content": "Too short",
        },
        "auto_fix": False,
    }
    doc_command = MegaAgentCommand(
        user_id="validator-demo",
        command_type=CommandType.VALIDATE,
        action="document",
        payload=doc_payload,
    )
    doc_response = await agent.handle_command(doc_command)
    print_section("Document Validation")
    print("success:", doc_response.success)
    print("error:", doc_response.error)
    pprint(doc_response.result)

    # Case data validation (passes)
    case_payload = {
        "validation_type": "case_data",
        "data": {
            "title": "Immigration Case",
            "description": "Extensive details about the immigration case and client background.",
            "case_type": "immigration",
            "client_id": "client-001",
        },
    }
    case_command = MegaAgentCommand(
        user_id="validator-demo",
        command_type=CommandType.VALIDATE,
        action="case",
        payload=case_payload,
    )
    case_response = await agent.handle_command(case_command)
    print_section("Case Validation")
    pprint(case_response.result)

    # Version comparison
    compare_payload = {
        "version1": {"title": "Draft", "content": "Initial version"},
        "version2": {"title": "Draft", "content": "Initial version updated"},
    }
    compare_command = MegaAgentCommand(
        user_id="validator-demo",
        command_type=CommandType.VALIDATE,
        action="compare_versions",
        payload=compare_payload,
    )
    compare_response = await agent.handle_command(compare_command)
    print_section("Version Comparison")
    pprint(compare_response.result)


if __name__ == "__main__":
    asyncio.run(main())
