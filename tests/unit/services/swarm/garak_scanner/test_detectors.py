"""Unit tests for services.swarm.garak_scanner.detectors module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from garak.attempt import Attempt

from services.swarm.garak_scanner.detectors import (
    load_detector,
    get_detector_triggers,
    run_detectors_on_attempt,
)


class TestLoadDetector:
    """Tests for load_detector function."""

    def test_should_load_detector_by_module_path(self):
        """Should load a detector from fully-qualified module path."""
        # Test that the function splits path correctly and attempts to load
        with patch('services.swarm.garak_scanner.detectors.importlib.import_module') as mock_import:
            with patch('services.swarm.garak_scanner.detectors.getattr') as mock_getattr:
                mock_module = Mock()
                mock_detector_instance = Mock()
                mock_detector_class = Mock(return_value=mock_detector_instance)

                mock_import.return_value = mock_module
                mock_getattr.return_value = mock_detector_class

                result = load_detector("garak.detectors.mitigation.MitigationBypass")

                # Verify import was called with correct module path
                mock_import.assert_called()
                # Should return a detector instance
                assert result is not None

    def test_should_add_garak_prefix_if_missing(self):
        """Should add 'garak.detectors.' prefix if not present."""
        with patch('services.swarm.garak_scanner.detectors.importlib.import_module') as mock_import:
            with patch('services.swarm.garak_scanner.detectors.getattr'):
                mock_module = Mock()
                mock_import.return_value = mock_module

                load_detector("mitigation.MitigationBypass")

                # Should call with full path
                call_args = mock_import.call_args[0][0]
                assert call_args.startswith("garak.detectors.")

    def test_should_handle_dotted_paths_correctly(self):
        """Should correctly split module path and class name."""
        with patch('services.swarm.garak_scanner.detectors.importlib.import_module') as mock_import:
            with patch('services.swarm.garak_scanner.detectors.getattr') as mock_getattr:
                mock_module = Mock()
                mock_detector_class = Mock(return_value=Mock())
                mock_import.return_value = mock_module
                mock_getattr.return_value = mock_detector_class

                load_detector("dan.DAN")

                # Should extract module and class correctly
                module_path = mock_import.call_args[0][0]
                assert "dan" in module_path.lower()


class TestGetDetectorTriggers:
    """Tests for get_detector_triggers function."""

    def test_should_include_probe_triggers_attribute(self):
        """Should include triggers from probe.triggers if present."""
        probe = Mock()
        probe.triggers = ["[DAN]", "DAN:", "trigger1"]
        probe.attack_rogue_string = None
        probe.goal = None
        probe.__class__.__name__ = "TestProbe"
        probe.__class__.__module__ = "test"

        result = get_detector_triggers(probe, "prompt", "output")

        assert "triggers" in result
        assert "[DAN]" in result["triggers"]
        assert "trigger1" in result["triggers"]

    def test_should_include_attack_rogue_string(self):
        """Should include attack_rogue_string from probe if present."""
        probe = Mock()
        probe.triggers = []
        probe.attack_rogue_string = "I hate humans"
        probe.goal = None
        probe.__class__.__name__ = "PromptInjectProbe"
        probe.__class__.__module__ = "test"

        result = get_detector_triggers(probe, "prompt", "output")

        assert "I hate humans" in result["triggers"]

    def test_should_add_dan_specific_triggers(self):
        """Should add DAN-specific triggers for DAN probes."""
        probe = Mock()
        probe.triggers = []
        probe.attack_rogue_string = None
        probe.goal = None
        probe.__class__.__name__ = "DANProbe"
        probe.__class__.__module__ = "garak.probes.jailbreak.dan"

        result = get_detector_triggers(probe, "prompt", "output")

        assert "[DAN]" in result["triggers"]
        assert "DAN:" in result["triggers"]
        assert "DAN Mode enabled" in result["triggers"]

    def test_should_add_promptinject_triggers(self):
        """Should add prompt injection specific triggers."""
        probe = Mock()
        probe.triggers = []
        probe.attack_rogue_string = None
        probe.goal = None
        probe.__class__.__name__ = "PromptInjectProbe"
        probe.__class__.__module__ = "garak.probes.injection.promptinject"

        result = get_detector_triggers(probe, "prompt", "output")

        assert "I hate humans" in result["triggers"]
        assert "i hate humans" in result["triggers"]

    def test_should_add_encoding_triggers(self):
        """Should add encoding-specific triggers."""
        probe = Mock()
        probe.triggers = []
        probe.attack_rogue_string = None
        probe.goal = None
        probe.__class__.__name__ = "EncodingProbe"
        probe.__class__.__module__ = "test"

        result = get_detector_triggers(probe, "prompt", "output")

        assert "decoded" in result["triggers"]
        assert "base64" in result["triggers"]
        assert "injection successful" in result["triggers"]

    def test_should_include_goal_if_present(self):
        """Should include probe goal in notes if present."""
        probe = Mock()
        probe.triggers = []
        probe.attack_rogue_string = None
        probe.goal = "Bypass authentication"
        probe.__class__.__name__ = "TestProbe"
        probe.__class__.__module__ = "test"

        result = get_detector_triggers(probe, "prompt", "output")

        assert result.get("goal") == "Bypass authentication"

    def test_should_handle_probe_without_attributes(self):
        """Should handle probes that lack optional attributes."""
        probe = Mock(spec=[])  # Minimal spec
        probe.__class__.__name__ = "MinimalProbe"
        probe.__class__.__module__ = "test"

        result = get_detector_triggers(probe, "prompt", "output")

        assert "triggers" in result
        assert isinstance(result["triggers"], list)


class TestRunDetectorsOnAttempt:
    """Tests for run_detectors_on_attempt function."""

    def test_should_use_recommended_detector_from_probe(self, mock_probe_with_recommended_detector):
        """Should use recommended_detector from probe (e.g., DAN probes)."""
        attempt = Mock(spec=Attempt)
        attempt.prompt = "test prompt"

        with patch('services.swarm.garak_scanner.detectors.load_detector') as mock_load:
            mock_detector = Mock()
            mock_detector.detect = Mock(return_value=[0.8])
            mock_load.return_value = mock_detector

            results = run_detectors_on_attempt(attempt, mock_probe_with_recommended_detector)

            # Should have loaded both recommended detectors
            assert mock_load.call_count >= 2
            # Check that recommended detectors were in the calls
            detector_paths = [call[0][0] for call in mock_load.call_args_list]
            assert "mitigation.MitigationBypass" in detector_paths
            assert "dan.DAN" in detector_paths

    def test_should_prioritize_primary_detector(self, mock_probe_with_primary_detector):
        """Should prioritize primary_detector over other detector types."""
        attempt = Mock(spec=Attempt)

        with patch('services.swarm.garak_scanner.detectors.load_detector') as mock_load:
            mock_detector = Mock()
            mock_detector.detect = Mock(return_value=[0.5])
            mock_load.return_value = mock_detector

            results = run_detectors_on_attempt(attempt, mock_probe_with_primary_detector)

            # Primary detector should be loaded first
            first_call = mock_load.call_args_list[0][0][0]
            assert first_call == "custom.CustomDetector"

    def test_should_use_extended_detectors(self):
        """Should include extended_detectors from probe."""
        probe = Mock()
        probe.__class__.__name__ = "TestProbe"
        probe.primary_detector = None
        probe.recommended_detector = None
        probe.extended_detectors = ["custom.Detector1", "custom.Detector2"]
        probe.default_detectors = None

        attempt = Mock(spec=Attempt)

        with patch('services.swarm.garak_scanner.detectors.load_detector') as mock_load:
            mock_detector = Mock()
            mock_detector.detect = Mock(return_value=[0.3])
            mock_load.return_value = mock_detector

            results = run_detectors_on_attempt(attempt, probe)

            detector_paths = [call[0][0] for call in mock_load.call_args_list]
            assert "custom.Detector1" in detector_paths
            assert "custom.Detector2" in detector_paths

    def test_should_use_default_detectors_fallback(self):
        """Should use default_detectors as fallback."""
        probe = Mock()
        probe.__class__.__name__ = "OldProbe"
        probe.primary_detector = None
        probe.recommended_detector = None
        probe.extended_detectors = None
        probe.default_detectors = ["garak.detectors.default.DefaultDetector"]

        attempt = Mock(spec=Attempt)

        with patch('services.swarm.garak_scanner.detectors.load_detector') as mock_load:
            mock_detector = Mock()
            mock_detector.detect = Mock(return_value=[0.2])
            mock_load.return_value = mock_detector

            results = run_detectors_on_attempt(attempt, probe)

            detector_paths = [call[0][0] for call in mock_load.call_args_list]
            assert any("DefaultDetector" in path for path in detector_paths)

    def test_should_always_include_mitigation_bypass_fallback(self, mock_probe_no_detectors):
        """Should always include MitigationBypass as fallback detector."""
        attempt = Mock(spec=Attempt)

        with patch('services.swarm.garak_scanner.detectors.load_detector') as mock_load:
            mock_detector = Mock()
            mock_detector.detect = Mock(return_value=[0.4])
            mock_load.return_value = mock_detector

            results = run_detectors_on_attempt(attempt, mock_probe_no_detectors)

            detector_paths = [call[0][0] for call in mock_load.call_args_list]
            assert "mitigation.MitigationBypass" in detector_paths

    def test_should_remove_duplicate_detectors(self):
        """Should not load the same detector twice."""
        probe = Mock()
        probe.__class__.__name__ = "DuplicateProbe"
        probe.primary_detector = "custom.SharedDetector"
        probe.recommended_detector = ["custom.SharedDetector", "custom.OtherDetector"]
        probe.extended_detectors = None
        probe.default_detectors = None

        attempt = Mock(spec=Attempt)

        with patch('services.swarm.garak_scanner.detectors.load_detector') as mock_load:
            mock_detector = Mock()
            mock_detector.detect = Mock(return_value=[0.5])
            mock_load.return_value = mock_detector

            results = run_detectors_on_attempt(attempt, probe)

            # Count how many times SharedDetector was loaded
            load_calls = mock_load.call_args_list
            shared_detector_calls = [
                call for call in load_calls
                if "SharedDetector" in str(call[0][0])
            ]
            # Should only load once (or not at all due to dedup)
            assert len(shared_detector_calls) <= 1

    def test_should_return_dict_mapping_detector_to_scores(self, mock_probe_no_detectors):
        """Should return dict mapping detector names to score lists."""
        attempt = Mock(spec=Attempt)

        with patch('services.swarm.garak_scanner.detectors.load_detector') as mock_load:
            mock_detector = Mock()
            mock_detector.detect = Mock(return_value=[0.7, 0.8, 0.6])
            mock_load.return_value = mock_detector

            results = run_detectors_on_attempt(attempt, mock_probe_no_detectors)

            assert isinstance(results, dict)
            for detector_name, scores in results.items():
                assert isinstance(detector_name, str)
                assert isinstance(scores, list)
                assert all(isinstance(s, (int, float)) for s in scores)

    def test_should_handle_detector_load_failure_gracefully(self, mock_probe_no_detectors):
        """Should handle detector loading failures and continue."""
        attempt = Mock(spec=Attempt)

        with patch('services.swarm.garak_scanner.detectors.load_detector') as mock_load:
            mock_load.side_effect = Exception("Detector not found")

            results = run_detectors_on_attempt(attempt, mock_probe_no_detectors)

            # Should still return dict with failed detectors mapped to [0.0]
            assert isinstance(results, dict)
            # All values should be [0.0] when loading fails
            for scores in results.values():
                assert scores == [0.0]

    def test_should_handle_detector_detect_failure_gracefully(self, mock_probe_no_detectors):
        """Should handle failures during detect() call."""
        attempt = Mock(spec=Attempt)

        with patch('services.swarm.garak_scanner.detectors.load_detector') as mock_load:
            mock_detector = Mock()
            mock_detector.detect.side_effect = Exception("Detection failed")
            mock_load.return_value = mock_detector

            results = run_detectors_on_attempt(attempt, mock_probe_no_detectors)

            # Should still return dict with [0.0] for failed detectors
            assert isinstance(results, dict)
            for scores in results.values():
                assert scores == [0.0]

    def test_should_handle_multiple_detector_scores(self, mock_probe_no_detectors):
        """Should handle detectors that return multiple scores."""
        attempt = Mock(spec=Attempt)

        with patch('services.swarm.garak_scanner.detectors.load_detector') as mock_load:
            mock_detector = Mock()
            # Some detectors return multiple scores (one per generation)
            mock_detector.detect = Mock(return_value=[0.1, 0.5, 0.9, 0.3])
            mock_load.return_value = mock_detector

            results = run_detectors_on_attempt(attempt, mock_probe_no_detectors)

            assert len(results) > 0
            for detector_name, scores in results.items():
                assert isinstance(scores, list)
                assert len(scores) > 0

    def test_should_use_recommended_detector_list_when_provided(self, mock_probe_with_recommended_detector):
        """Should handle recommended_detector as a list."""
        attempt = Mock(spec=Attempt)

        with patch('services.swarm.garak_scanner.detectors.load_detector') as mock_load:
            mock_detector = Mock()
            mock_detector.detect = Mock(return_value=[0.5])
            mock_load.return_value = mock_detector

            results = run_detectors_on_attempt(attempt, mock_probe_with_recommended_detector)

            # Should call load_detector for each detector in the list
            assert mock_load.call_count >= 2

    def test_should_maintain_detector_order_priority(self):
        """Should follow priority order: primary > recommended > extended > default > fallback."""
        probe = Mock()
        probe.__class__.__name__ = "PriorityProbe"
        probe.primary_detector = "primary.Detector"
        probe.recommended_detector = ["rec.Detector"]
        probe.extended_detectors = ["ext.Detector"]
        probe.default_detectors = ["def.Detector"]

        attempt = Mock(spec=Attempt)

        with patch('services.swarm.garak_scanner.detectors.load_detector') as mock_load:
            mock_detector = Mock()
            mock_detector.detect = Mock(return_value=[0.5])
            mock_load.return_value = mock_detector

            results = run_detectors_on_attempt(attempt, probe)

            # Get the order of load calls
            call_paths = [call[0][0] for call in mock_load.call_args_list]

            # Primary should come first
            primary_idx = next(
                (i for i, path in enumerate(call_paths) if "primary" in path),
                float('inf')
            )

            # Recommended should come before extended
            rec_idx = next(
                (i for i, path in enumerate(call_paths) if "rec" in path),
                float('inf')
            )
            ext_idx = next(
                (i for i, path in enumerate(call_paths) if "ext" in path),
                float('inf')
            )

            assert primary_idx < rec_idx
            assert rec_idx < ext_idx
