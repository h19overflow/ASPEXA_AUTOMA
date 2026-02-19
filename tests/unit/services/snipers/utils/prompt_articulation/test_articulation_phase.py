"""
Unit tests for ArticulationPhase - payload articulation orchestrator.

Purpose: Verify that payload generation correctly routes through custom framing,
recon-based custom framing, and standard framing with proper priority ordering.

Dependencies: ArticulationPhase, PayloadGenerator, FramingLibrary
System Role: Unit test layer
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.snipers.core.phases.articulation.articulation_phase import ArticulationPhase
from services.snipers.core.phases.articulation.models import (
    PayloadContext,
    TargetInfo,
    AttackHistory,
    FramingType,
    FramingStrategy,
)
from services.snipers.models import Phase1Result


class TestArticulationPhaseInit:
    """Test ArticulationPhase initialization."""

    def test_articulation_phase_creation_with_default_llm(self):
        """Test that ArticulationPhase creates with default LLM."""
        phase = ArticulationPhase()
        assert phase.loader is not None
        assert phase.extractor is not None
        assert phase.llm is not None

    def test_articulation_phase_creation_with_custom_llm(self):
        """Test that ArticulationPhase accepts custom LLM."""
        mock_llm = MagicMock()
        phase = ArticulationPhase(llm=mock_llm)
        assert phase.llm is mock_llm


class TestArticulationPhaseFraming:
    """Test framing type resolution and strategy selection."""

    def setup_method(self):
        """Initialize test fixtures."""
        self.mock_llm = MagicMock()
        self.phase = ArticulationPhase(llm=self.mock_llm)

    def test_resolve_framing_types_with_valid_list(self):
        """Test that valid framing types are parsed correctly."""
        library = MagicMock()
        requested = ["qa_testing", "debugging"]

        result = self.phase._resolve_framing_types(requested, 2, library)

        assert len(result) == 2
        assert result[0] == FramingType.QA_TESTING
        assert result[1] == FramingType.DEBUGGING

    def test_resolve_framing_types_with_invalid_falls_back(self):
        """Test that invalid framing types fall back to QA_TESTING."""
        library = MagicMock()
        requested = ["invalid_type"]

        result = self.phase._resolve_framing_types(requested, 1, library)

        assert len(result) == 1
        assert result[0] == FramingType.QA_TESTING

    def test_resolve_framing_types_cycles_when_more_payloads_than_types(self):
        """Test that framing types cycle when payload count exceeds type count."""
        library = MagicMock()
        requested = ["qa_testing"]

        result = self.phase._resolve_framing_types(requested, 3, library)

        assert len(result) == 3
        assert result[0] == FramingType.QA_TESTING
        assert result[1] == FramingType.QA_TESTING
        assert result[2] == FramingType.QA_TESTING

    def test_resolve_framing_types_auto_select_none(self):
        """Test auto-selection when no types requested."""
        library = MagicMock()
        strategy = FramingStrategy(
            type=FramingType.QA_TESTING,
            name="qa",
            system_context="test",
            user_prefix="test",
            user_suffix="",
            domain_effectiveness={},
            detection_risk="low",
        )
        library.get_strategy.return_value = strategy

        result = self.phase._resolve_framing_types(None, 2, library)

        assert len(result) == 2
        assert all(isinstance(ft, FramingType) for ft in result)


class TestArticulationPhaseContextBuilding:
    """Test PayloadContext building from campaign intelligence."""

    def setup_method(self):
        """Initialize test fixtures."""
        self.mock_llm = MagicMock()
        self.phase = ArticulationPhase(llm=self.mock_llm)

    def test_build_context_with_basic_intel(self):
        """Test context building with minimal intelligence."""
        mock_intel = MagicMock()
        mock_intel.domain = "ecommerce"
        mock_intel.tools = ["checkout", "search"]
        mock_intel.defense_patterns = ["rate_limit"]
        mock_intel.objective = "checkout an order"
        mock_intel.recon_raw = {"intelligence": {"infrastructure": {}}}

        mock_recon_intel = MagicMock()
        mock_recon_intel.tools = []

        context = self.phase._build_context(mock_intel, mock_recon_intel, None)

        assert context.target.domain == "ecommerce"
        assert context.target.tools == ["checkout", "search"]
        assert context.observed_defenses == ["rate_limit"]
        assert context.objective == "checkout an order"
        assert context.recon_custom_framing is None

    def test_build_context_with_recon_custom_framing(self):
        """Test context building with recon-based custom framing."""
        mock_intel = MagicMock()
        mock_intel.domain = "finance"
        mock_intel.tools = []
        mock_intel.defense_patterns = []
        mock_intel.objective = "transfer funds"
        mock_intel.recon_raw = {"intelligence": {"infrastructure": {}}}

        mock_recon_intel = MagicMock()
        mock_recon_intel.tools = []

        recon_framing = {
            "role": "customer",
            "context": "making a transfer",
            "justification": "target identifies as banking service",
        }

        context = self.phase._build_context(mock_intel, mock_recon_intel, recon_framing)

        assert context.recon_custom_framing == recon_framing
        assert context.recon_custom_framing["role"] == "customer"


class TestGenerateReconFraming:
    """Test the new _generate_recon_framing method."""

    def setup_method(self):
        """Initialize test fixtures."""
        self.mock_llm = MagicMock()
        self.phase = ArticulationPhase(llm=self.mock_llm)

    @pytest.mark.asyncio
    async def test_generate_recon_framing_success(self):
        """Test successful payload generation with recon framing."""
        mock_generator = MagicMock()
        mock_payload = MagicMock()
        mock_payload.content = "test payload content"
        mock_generator.generate = AsyncMock(return_value=mock_payload)

        context = MagicMock()
        recon_framing = {
            "role": "customer",
            "context": "making a transfer",
            "justification": "banking alignment",
        }

        payloads, framing_names = await self.phase._generate_recon_framing(
            mock_generator, context, recon_framing, count=1, use_tagged=False, campaign_id="test"
        )

        assert len(payloads) == 1
        assert payloads[0] == "test payload content"
        assert len(framing_names) == 1
        assert "recon_customer" in framing_names[0]

    @pytest.mark.asyncio
    async def test_generate_recon_framing_multiple_payloads(self):
        """Test generation of multiple payloads with recon framing."""
        mock_generator = MagicMock()
        mock_payload = MagicMock()
        mock_payload.content = "test payload"
        mock_generator.generate = AsyncMock(return_value=mock_payload)

        context = MagicMock()
        recon_framing = {
            "role": "admin",
            "context": "security audit",
            "justification": "admin system alignment",
        }

        payloads, framing_names = await self.phase._generate_recon_framing(
            mock_generator, context, recon_framing, count=3, use_tagged=False, campaign_id="test"
        )

        assert len(payloads) == 3
        assert len(framing_names) == 3
        assert all("recon_admin" in name for name in framing_names)

    @pytest.mark.asyncio
    async def test_generate_recon_framing_creates_custom_strategy(self):
        """Test that recon framing creates and uses a custom strategy."""
        mock_generator = MagicMock()
        mock_generator.framing_library = MagicMock()
        mock_generator.framing_library.strategies = {}

        mock_payload = MagicMock()
        mock_payload.content = "payload"
        mock_generator.generate = AsyncMock(return_value=mock_payload)

        context = MagicMock()
        recon_framing = {
            "role": "analyst",
            "context": "data review",
            "justification": "analyst alignment",
        }

        await self.phase._generate_recon_framing(
            mock_generator, context, recon_framing, count=1, use_tagged=False, campaign_id="test"
        )

        # Verify that a custom strategy was created
        assert FramingType.QA_TESTING in mock_generator.framing_library.strategies
        strategy = mock_generator.framing_library.strategies[FramingType.QA_TESTING]
        assert "analyst" in strategy.system_context

    @pytest.mark.asyncio
    async def test_generate_recon_framing_retry_on_failure(self):
        """Test that recon framing retries on generation failure."""
        mock_generator = MagicMock()
        mock_payload = MagicMock()
        mock_payload.content = "success"

        # Fail twice, then succeed
        mock_generator.generate = AsyncMock(
            side_effect=[Exception("failure"), Exception("failure"), mock_payload]
        )

        context = MagicMock()
        recon_framing = {
            "role": "user",
            "context": "normal interaction",
            "justification": "user alignment",
        }

        payloads, _ = await self.phase._generate_recon_framing(
            mock_generator, context, recon_framing, count=1, use_tagged=False, campaign_id="test"
        )

        assert len(payloads) == 1
        assert payloads[0] == "success"


class TestGenerateCustomFraming:
    """Test the _generate_custom method."""

    def setup_method(self):
        """Initialize test fixtures."""
        self.mock_llm = MagicMock()
        self.phase = ArticulationPhase(llm=self.mock_llm)

    @pytest.mark.asyncio
    async def test_generate_custom_success(self):
        """Test successful payload generation with custom framing."""
        mock_generator = MagicMock()
        mock_generator.framing_library = MagicMock()
        mock_generator.framing_library.strategies = {}

        mock_payload = MagicMock()
        mock_payload.content = "custom payload"
        mock_generator.generate = AsyncMock(return_value=mock_payload)

        context = MagicMock()
        custom_framing = {
            "name": "my_custom",
            "system_context": "act as X",
            "user_prefix": "prefix",
            "user_suffix": "suffix",
        }

        payloads, framing_names = await self.phase._generate_custom(
            mock_generator, context, custom_framing, count=1, campaign_id="test"
        )

        assert len(payloads) == 1
        assert payloads[0] == "custom payload"
        assert framing_names[0] == "my_custom"

    @pytest.mark.asyncio
    async def test_generate_custom_multiple_payloads(self):
        """Test generation of multiple payloads with custom framing."""
        mock_generator = MagicMock()
        mock_generator.framing_library = MagicMock()
        mock_generator.framing_library.strategies = {}

        mock_payload = MagicMock()
        mock_payload.content = "payload"
        mock_generator.generate = AsyncMock(return_value=mock_payload)

        context = MagicMock()
        custom_framing = {"name": "custom", "system_context": "test", "user_prefix": "", "user_suffix": ""}

        payloads, framing_names = await self.phase._generate_custom(
            mock_generator, context, custom_framing, count=2, campaign_id="test"
        )

        assert len(payloads) == 2
        assert len(framing_names) == 2
        assert framing_names[0] == "custom_1"
        assert framing_names[1] == "custom_2"


class TestExecutePriorityRouting:
    """Test the execute method's framing priority routing."""

    def setup_method(self):
        """Initialize test fixtures."""
        self.mock_llm = MagicMock()
        self.phase = ArticulationPhase(llm=self.mock_llm)

    @pytest.mark.asyncio
    async def test_execute_routes_to_custom_framing_when_provided(self):
        """Test that custom_framing takes priority over recon_custom_framing."""
        with patch.object(self.phase, 'loader') as mock_loader, \
             patch.object(self.phase, 'extractor') as mock_extractor, \
             patch.object(self.phase, '_generate_custom') as mock_custom, \
             patch.object(self.phase, '_generate_recon_framing') as mock_recon:

            mock_custom.return_value = (["custom_payload"], ["custom"])
            mock_intel = MagicMock()
            mock_intel.tools = []
            mock_intel.domain = "test"
            mock_intel.objective = "test objective"
            mock_intel.defense_patterns = []
            mock_intel.recon_raw = {"intelligence": {"infrastructure": {}}}
            mock_loader.load = AsyncMock(return_value=mock_intel)

            mock_recon_intel = MagicMock()
            mock_recon_intel.tools = []
            mock_extractor.extract.return_value = mock_recon_intel

            custom_framing = {"name": "custom"}
            recon_custom_framing = {"role": "user"}

            result = await self.phase.execute(
                campaign_id="test",
                custom_framing=custom_framing,
                recon_custom_framing=recon_custom_framing,
            )

            # Verify that _generate_custom was called
            mock_custom.assert_called_once()
            # Verify that _generate_recon_framing was NOT called
            mock_recon.assert_not_called()
            assert result.articulated_payloads == ["custom_payload"]

    @pytest.mark.asyncio
    async def test_execute_routes_to_recon_framing_when_no_custom(self):
        """Test that recon_custom_framing is used when custom_framing is None."""
        with patch.object(self.phase, 'loader') as mock_loader, \
             patch.object(self.phase, 'extractor') as mock_extractor, \
             patch.object(self.phase, '_generate_recon_framing') as mock_recon, \
             patch.object(self.phase, '_generate_standard') as mock_standard:

            mock_recon.return_value = (["recon_payload"], ["recon"])
            mock_intel = MagicMock()
            mock_intel.tools = []
            mock_intel.domain = "test"
            mock_intel.objective = "test objective"
            mock_intel.defense_patterns = []
            mock_intel.recon_raw = {"intelligence": {"infrastructure": {}}}
            mock_loader.load = AsyncMock(return_value=mock_intel)

            mock_recon_intel = MagicMock()
            mock_recon_intel.tools = []
            mock_extractor.extract.return_value = mock_recon_intel

            recon_custom_framing = {"role": "customer", "context": "purchase", "justification": "alignment"}

            result = await self.phase.execute(
                campaign_id="test",
                recon_custom_framing=recon_custom_framing,
            )

            # Verify that _generate_recon_framing was called
            mock_recon.assert_called_once()
            # Verify that _generate_standard was NOT called
            mock_standard.assert_not_called()
            assert result.articulated_payloads == ["recon_payload"]

    @pytest.mark.asyncio
    async def test_execute_routes_to_standard_when_no_custom_or_recon(self):
        """Test that standard framing is used as fallback."""
        with patch.object(self.phase, 'loader') as mock_loader, \
             patch.object(self.phase, 'extractor') as mock_extractor, \
             patch.object(self.phase, '_generate_standard') as mock_standard:

            mock_standard.return_value = (["standard_payload"], [FramingType.QA_TESTING])
            mock_intel = MagicMock()
            mock_intel.tools = []
            mock_intel.domain = "test"
            mock_intel.objective = "test objective"
            mock_intel.defense_patterns = []
            mock_intel.recon_raw = {"intelligence": {"infrastructure": {}}}
            mock_loader.load = AsyncMock(return_value=mock_intel)

            mock_recon_intel = MagicMock()
            mock_recon_intel.tools = []
            mock_extractor.extract.return_value = mock_recon_intel

            result = await self.phase.execute(campaign_id="test")

            # Verify that _generate_standard was called
            mock_standard.assert_called_once()
            assert result.articulated_payloads == ["standard_payload"]

    @pytest.mark.asyncio
    async def test_execute_priority_custom_over_recon_and_standard(self):
        """Test full priority ordering: custom > recon > standard."""
        with patch.object(self.phase, 'loader') as mock_loader, \
             patch.object(self.phase, 'extractor') as mock_extractor, \
             patch.object(self.phase, '_generate_custom') as mock_custom, \
             patch.object(self.phase, '_generate_recon_framing') as mock_recon, \
             patch.object(self.phase, '_generate_standard') as mock_standard:

            mock_custom.return_value = (["custom"], ["custom"])
            mock_intel = MagicMock()
            mock_intel.tools = []
            mock_intel.domain = "test"
            mock_intel.objective = "objective"
            mock_intel.defense_patterns = []
            mock_intel.recon_raw = {"intelligence": {"infrastructure": {}}}
            mock_loader.load = AsyncMock(return_value=mock_intel)

            mock_recon_intel = MagicMock()
            mock_recon_intel.tools = []
            mock_extractor.extract.return_value = mock_recon_intel

            await self.phase.execute(
                campaign_id="test",
                custom_framing={"name": "custom"},
                recon_custom_framing={"role": "user"},
                framing_types=["qa_testing"],
            )

            # Only custom should be called
            mock_custom.assert_called_once()
            mock_recon.assert_not_called()
            mock_standard.assert_not_called()


class TestGenerateStandard:
    """Test the _generate_standard method."""

    def setup_method(self):
        """Initialize test fixtures."""
        self.mock_llm = MagicMock()
        self.phase = ArticulationPhase(llm=self.mock_llm)

    @pytest.mark.asyncio
    async def test_generate_standard_success(self):
        """Test successful payload generation with standard framing."""
        mock_generator = MagicMock()
        mock_payload = MagicMock()
        mock_payload.content = "payload"
        mock_generator.generate = AsyncMock(return_value=mock_payload)

        context = MagicMock()
        library = MagicMock()

        payloads, framing_used = await self.phase._generate_standard(
            mock_generator, context, ["qa_testing"], count=1, library=library, use_tagged=False, campaign_id="test"
        )

        assert len(payloads) == 1
        assert payloads[0] == "payload"
        assert len(framing_used) == 1
        assert framing_used[0] == FramingType.QA_TESTING

    @pytest.mark.asyncio
    async def test_generate_standard_retry_on_failure(self):
        """Test that standard framing retries on failure."""
        mock_generator = MagicMock()
        mock_payload = MagicMock()
        mock_payload.content = "success"

        # Fail twice, then succeed
        mock_generator.generate = AsyncMock(
            side_effect=[Exception("fail"), Exception("fail"), mock_payload]
        )

        context = MagicMock()
        library = MagicMock()

        payloads, _ = await self.phase._generate_standard(
            mock_generator, context, ["qa_testing"], count=1, library=library, use_tagged=False, campaign_id="test"
        )

        assert len(payloads) == 1
        assert payloads[0] == "success"

    @pytest.mark.asyncio
    async def test_generate_standard_skip_on_max_retries(self):
        """Test that payload is skipped if max retries exceeded."""
        mock_generator = MagicMock()
        mock_generator.generate = AsyncMock(side_effect=Exception("always fails"))

        context = MagicMock()
        library = MagicMock()

        payloads, framing_used = await self.phase._generate_standard(
            mock_generator, context, ["qa_testing"], count=1, library=library, use_tagged=False, campaign_id="test"
        )

        # Should have no payloads since it failed all retries
        assert len(payloads) == 0
        assert len(framing_used) == 0
