"""ADK root agent. Run locally with `adk web` from sombrero/src to chat with it."""
from google.adk.agents import Agent

from ..config import get_settings
from . import code_decoder, policy_rules

settings = get_settings()

root_agent = Agent(
    name="kavach_orchestrator",
    model=settings.model_reasoning,
    description="Helps a patient contest a health-insurance claim rejection.",
    instruction=(
        "Work out why the claim was rejected, find the policy clause and regulations that apply, "
        "and explain the patient's options in plain language. Cite a source for every claim."
    ),
    tools=[code_decoder.decode, policy_rules.find_sections],
)
