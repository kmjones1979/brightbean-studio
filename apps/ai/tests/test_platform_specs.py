"""Tests for platform_specs."""

from __future__ import annotations

from apps.ai.platform_specs import PLATFORM_SPECS, get_spec, supported_platforms


class TestPlatformSpecs:
    def test_all_specs_have_positive_limits(self):
        for spec in PLATFORM_SPECS.values():
            assert spec.char_limit > 0
            assert spec.effective_limit < spec.char_limit
            assert spec.effective_limit > 0

    def test_known_platforms(self):
        assert "twitter" in PLATFORM_SPECS
        assert "linkedin_personal" in PLATFORM_SPECS
        assert "bluesky" in PLATFORM_SPECS

    def test_get_spec(self):
        spec = get_spec("twitter")
        assert spec is not None
        assert spec.char_limit == 280
        assert get_spec("nope") is None

    def test_supported_platforms_returns_list(self):
        platforms = supported_platforms()
        assert isinstance(platforms, list)
        assert "twitter" in platforms
