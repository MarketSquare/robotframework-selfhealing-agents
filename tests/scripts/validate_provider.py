#!/usr/bin/env python
"""Provider validation script for ADR-001 implementation.

This script validates that different LLM providers work correctly with
the self-healing agents. It tests the provider abstraction layer and
output strategy without requiring a full robot test.

Usage:
    # Test OpenAI (requires OPENAI_API_KEY)
    LOCATOR_AGENT_PROVIDER=openai OPENAI_API_KEY=sk-xxx python validate_provider.py

    # Test OpenRouter (requires OPENAI_API_KEY set to OpenRouter key)
    LOCATOR_AGENT_PROVIDER=openrouter OPENAI_API_KEY=sk-or-xxx python validate_provider.py

    # Test Ollama (requires local Ollama server)
    LOCATOR_AGENT_PROVIDER=ollama LOCATOR_AGENT_MODEL=qwen2.5:7b python validate_provider.py

    # Test LiteLLM (requires OPENAI_API_KEY or LITELLM_API_KEY)
    LOCATOR_AGENT_PROVIDER=litellm LOCATOR_AGENT_MODEL=gpt-4o-mini python validate_provider.py
"""
import asyncio
import os
import sys

# Add package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def validate_provider_config():
    """Validate the provider configuration."""
    from SelfhealingAgents.utils.cfg import Cfg
    from SelfhealingAgents.self_healing_system.llm.client_model import get_client_model
    from SelfhealingAgents.self_healing_system.llm.output_strategy import (
        resolve_structured_output_type,
        make_prepare_tools_hook,
    )
    from SelfhealingAgents.self_healing_system.schemas.api.locator_healing import (
        LocatorHealingResponse,
    )

    print("=" * 60)
    print("ADR-001 Provider Validation Test")
    print("=" * 60)

    # Load configuration from environment
    cfg = Cfg()
    provider = cfg.locator_agent_provider
    model = cfg.locator_agent_model

    print(f"\nProvider: {provider}")
    print(f"Model: {model}")
    print(f"Output Mode: {cfg.output_mode}")
    print(f"Strict Tool Definitions: {cfg.strict_tool_definitions}")

    # Test 1: Provider builder
    print("\n[Test 1] Provider Builder...")
    try:
        client_model = get_client_model(provider=provider, model=model, cfg=cfg)
        print(f"  ✓ Created client model: {type(client_model).__name__}")
    except Exception as e:
        print(f"  ✗ Failed to create client model: {e}")
        return False

    # Test 2: Output type resolution
    print("\n[Test 2] Output Type Resolution...")
    try:
        output_type = resolve_structured_output_type(LocatorHealingResponse, cfg, provider)
        print(f"  ✓ Output type resolved: {type(output_type).__name__}")
    except Exception as e:
        print(f"  ✗ Failed to resolve output type: {e}")
        return False

    # Test 3: Prepare tools hook
    print("\n[Test 3] Prepare Tools Hook...")
    try:
        hook = make_prepare_tools_hook(provider, cfg)
        if hook is None:
            print(f"  ✓ No prepare_tools hook needed for {provider}")
        else:
            print(f"  ✓ Prepare tools hook created: {hook.__name__}")
    except Exception as e:
        print(f"  ✗ Failed to create prepare tools hook: {e}")
        return False

    print("\n" + "=" * 60)
    print("All configuration tests passed!")
    print("=" * 60)

    return True


async def validate_provider_connectivity():
    """Validate provider connectivity with a simple LLM call."""
    from pydantic_ai import Agent
    from SelfhealingAgents.utils.cfg import Cfg
    from SelfhealingAgents.self_healing_system.llm.client_model import get_client_model

    cfg = Cfg()
    provider = cfg.locator_agent_provider
    model = cfg.locator_agent_model

    print(f"\n[Test 4] Provider Connectivity ({provider})...")

    try:
        client_model = get_client_model(provider=provider, model=model, cfg=cfg)

        # Create a simple agent
        agent = Agent(
            model=client_model,
            system_prompt="You are a helpful assistant. Respond with 'OK' if you receive this message.",
        )

        # Make a simple call
        result = await agent.run("Test message. Respond with just 'OK'.")

        if result.output:
            print(f"  ✓ Provider responded: {result.output[:50]}...")
            return True
        else:
            print(f"  ✗ Provider returned empty response")
            return False

    except Exception as e:
        print(f"  ✗ Provider connectivity failed: {e}")
        return False


def main():
    """Run provider validation."""
    # Test 1-3: Configuration tests (no API calls)
    if not validate_provider_config():
        sys.exit(1)

    # Test 4: Connectivity test (requires API key)
    api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('LITELLM_API_KEY')
    provider = os.environ.get('LOCATOR_AGENT_PROVIDER', 'openai')

    if provider == 'ollama':
        # Ollama doesn't need API key
        print("\n[Connectivity Test] Running Ollama connectivity test...")
        success = asyncio.run(validate_provider_connectivity())
    elif api_key:
        print("\n[Connectivity Test] API key found, running connectivity test...")
        success = asyncio.run(validate_provider_connectivity())
    else:
        print("\n[Connectivity Test] Skipped - No API key set")
        print("  Set OPENAI_API_KEY to test provider connectivity")
        success = True  # Skip connectivity test

    if success:
        print("\n✓ All validation tests passed!")
    else:
        print("\n✗ Validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
