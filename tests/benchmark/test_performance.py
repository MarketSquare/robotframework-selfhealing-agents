"""Performance benchmark tests for ADR-001 implementation.

Measures key performance metrics:
- Error classification latency (should be <1ms for tier-1)
- Output strategy resolution latency
- Schema sanitization latency
"""
import pytest
import time
from unittest.mock import MagicMock

from pydantic import BaseModel, Field


class BenchmarkSchema(BaseModel):
    """Schema for benchmark tests."""
    suggestions: list[str] = Field(default_factory=list)
    metadata: list[dict] = Field(default_factory=list)


class TestErrorClassificationBenchmark:
    """Benchmark tests for error classification."""

    def test_tier1_classification_latency(self):
        """Tier-1 classification should complete in <1ms."""
        from SelfhealingAgents.self_healing_system.error_classification import classify_error

        error_msg = "Element with locator 'css:#btn' not found."

        # Warmup
        for _ in range(10):
            classify_error(error_msg)

        # Benchmark
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            classify_error(error_msg)
        elapsed = time.perf_counter() - start

        avg_latency_ms = (elapsed / iterations) * 1000

        print(f"\nTier-1 classification avg latency: {avg_latency_ms:.3f}ms")
        assert avg_latency_ms < 1.0, f"Classification too slow: {avg_latency_ms:.3f}ms"

    def test_pattern_registry_scaling(self):
        """Pattern registry should scale with number of patterns."""
        from SelfhealingAgents.self_healing_system.error_classification.error_classifier import (
            PatternRegistry,
        )
        from SelfhealingAgents.self_healing_system.error_classification.healing_types import (
            HealingType,
        )

        registry = PatternRegistry()

        # Add many patterns
        for i in range(100):
            registry.register(
                f"test_pattern_{i}",
                HealingType.LOCATOR,
                f"Test pattern {i}"
            )

        # Benchmark with many patterns
        error_msg = "Unknown error that won't match"

        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            registry.classify(error_msg)
        elapsed = time.perf_counter() - start

        avg_latency_ms = (elapsed / iterations) * 1000

        print(f"\nRegistry with 100+ patterns avg latency: {avg_latency_ms:.3f}ms")
        # Should still be fast even with many patterns
        assert avg_latency_ms < 5.0, f"Registry too slow with many patterns: {avg_latency_ms:.3f}ms"


class TestOutputStrategyBenchmark:
    """Benchmark tests for output strategy resolution."""

    def test_output_resolution_latency(self):
        """Output strategy resolution should be fast."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import resolve_structured_output_type

        cfg = MagicMock()
        cfg.output_mode = "auto"

        # Warmup
        for _ in range(10):
            resolve_structured_output_type(BenchmarkSchema, cfg, "openai")

        # Benchmark
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            resolve_structured_output_type(BenchmarkSchema, cfg, "openai")
        elapsed = time.perf_counter() - start

        avg_latency_ms = (elapsed / iterations) * 1000

        print(f"\nOutput resolution avg latency: {avg_latency_ms:.3f}ms")
        assert avg_latency_ms < 1.0, f"Output resolution too slow: {avg_latency_ms:.3f}ms"

    def test_prepare_tools_hook_latency(self):
        """prepare_tools hook creation should be fast."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import make_prepare_tools_hook

        cfg = MagicMock()

        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            make_prepare_tools_hook("ollama", cfg)
        elapsed = time.perf_counter() - start

        avg_latency_ms = (elapsed / iterations) * 1000

        print(f"\nprepare_tools hook creation avg latency: {avg_latency_ms:.3f}ms")
        assert avg_latency_ms < 0.1, f"Hook creation too slow: {avg_latency_ms:.3f}ms"


class TestSchemaSanitizationBenchmark:
    """Benchmark tests for schema sanitization."""

    def test_strip_strict_latency(self):
        """Schema sanitization should be sub-millisecond."""
        from SelfhealingAgents.self_healing_system.llm.output_strategy import _strip_strict_from_schema

        # Complex nested schema
        schema = {
            "type": "object",
            "strict": True,
            "additionalProperties": False,
            "properties": {
                "suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "strict": True,
                        "additionalProperties": False,
                        "properties": {
                            "locator": {"type": "string"},
                            "confidence": {"type": "number"},
                        }
                    }
                },
                "metadata": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "strict": True,
                        "properties": {
                            "key": {"type": "string"},
                            "value": {"type": "string"},
                        }
                    }
                }
            }
        }

        import copy

        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            test_schema = copy.deepcopy(schema)
            _strip_strict_from_schema(test_schema)
        elapsed = time.perf_counter() - start

        avg_latency_ms = (elapsed / iterations) * 1000

        print(f"\nSchema sanitization avg latency: {avg_latency_ms:.3f}ms")
        assert avg_latency_ms < 1.0, f"Sanitization too slow: {avg_latency_ms:.3f}ms"


class TestMemoryBenchmark:
    """Memory usage benchmarks."""

    def test_pattern_registry_memory(self):
        """Pattern registry should have reasonable memory footprint."""
        import sys
        from SelfhealingAgents.self_healing_system.error_classification.error_classifier import PatternRegistry
        from SelfhealingAgents.self_healing_system.error_classification.healing_types import HealingType

        # Get baseline - note: PatternRegistry is a singleton, so we measure
        # the existing instance with its default patterns
        registry = PatternRegistry()

        initial_pattern_count = len(registry._patterns)
        base_size = sys.getsizeof(registry._patterns)

        # Add additional patterns
        for i in range(100):
            registry.register(f"pattern_{i}", HealingType.LOCATOR, f"desc_{i}")

        final_size = sys.getsizeof(registry._patterns)

        print(f"\nPatternRegistry memory: base={base_size}B, final={final_size}B")
        print(f"Initial patterns: {initial_pattern_count}, Final patterns: {len(registry._patterns)}")
        # Should be reasonable (patterns are compiled regex which are efficient)
        assert final_size < 100000, f"Registry using too much memory: {final_size}B"
