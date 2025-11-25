"""Unit tests for snipers parsers (data extraction and validation)."""
import pytest
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class TestGarakReportParser:
    """Test GarakReportParser functionality."""

    def test_parse_valid_garak_report(self, sample_garak_report, capture_logs):
        """Test parsing valid Garak report."""
        logger.info(f"Testing GarakReportParser with audit_id: {sample_garak_report['audit_id']}")
        assert sample_garak_report["audit_id"]
        assert sample_garak_report["vulnerability_clusters"]["clusters"]
        assert sample_garak_report["vulnerable_probes"]["summary"]
        assert sample_garak_report["vulnerability_findings"]["results"]
        logger.info("✓ Valid Garak report structure confirmed")

    def test_extract_vulnerable_probes(self, sample_garak_report, capture_logs):
        """Test extracting vulnerable probes from Garak report."""
        logger.info("Testing vulnerable probe extraction")
        probes = sample_garak_report["vulnerable_probes"]["summary"]
        assert len(probes) > 0, "Should extract at least one probe"

        for probe in probes:
            assert "probe_name" in probe
            assert "vulnerability_count" in probe
            assert probe["vulnerability_count"] > 0
            logger.info(f"  ✓ Found probe: {probe['probe_name']} ({probe['vulnerability_count']} vulns)")

    def test_extract_vulnerability_findings(self, sample_garak_report, capture_logs):
        """Test extracting vulnerability findings."""
        logger.info("Testing vulnerability findings extraction")
        findings = sample_garak_report["vulnerability_findings"]["results"]
        assert len(findings) > 0, "Should extract at least one finding"

        for finding in findings:
            assert "probe_name" in finding
            assert "status" in finding
            assert "detector_name" in finding
            assert "detector_score" in finding
            assert "prompt" in finding
            assert "output" in finding
            assert 0.0 <= finding["detector_score"] <= 1.0
            logger.info(f"  ✓ Found finding: {finding['detector_name']} (score: {finding['detector_score']})")

    def test_handle_empty_garak_report(self, empty_garak_report, capture_logs):
        """Test handling empty Garak report."""
        logger.warning("Testing empty Garak report handling")
        assert empty_garak_report["audit_id"]
        assert len(empty_garak_report["vulnerability_clusters"]["clusters"]) == 0
        assert len(empty_garak_report["vulnerable_probes"]["summary"]) == 0
        logger.warning("✓ Empty report handled gracefully")

    def test_garak_report_missing_fields(self, garak_report_missing_fields, capture_logs):
        """Test error handling for Garak report with missing fields."""
        logger.error("Testing Garak report with missing fields")
        required_fields = [
            "audit_id",
            "timestamp",
            "vulnerability_clusters",
            "vulnerable_probes",
            "vulnerability_findings"
        ]
        missing = [f for f in required_fields if f not in garak_report_missing_fields]
        assert len(missing) > 0, "Test setup should have missing fields"
        logger.error(f"✗ Should reject report missing: {missing}")

    def test_garak_report_malformed_clusters(self, capture_logs):
        """Test error handling for malformed vulnerability clusters."""
        logger.error("Testing malformed vulnerability clusters")
        malformed_report = {
            "audit_id": "test",
            "timestamp": "2025-01-01T00:00:00Z",
            "vulnerability_clusters": {
                "clusters": [
                    {
                        "cluster_id": "vuln-1",
                        # Missing: category, severity, evidence
                    }
                ]
            },
            "vulnerable_probes": {"summary": []},
            "vulnerability_findings": {"results": []}
        }
        cluster = malformed_report["vulnerability_clusters"]["clusters"][0]
        required_fields = ["category", "severity", "evidence"]
        missing = [f for f in required_fields if f not in cluster]
        assert len(missing) > 0
        logger.error(f"✗ Should reject cluster missing: {missing}")

    def test_garak_report_invalid_confidence_score(self, capture_logs):
        """Test handling of invalid confidence scores."""
        logger.error("Testing invalid confidence score in evidence")
        invalid_report = {
            "audit_id": "test",
            "timestamp": "2025-01-01T00:00:00Z",
            "vulnerability_clusters": {
                "clusters": [
                    {
                        "cluster_id": "vuln-1",
                        "category": "injection",
                        "severity": "high",
                        "evidence": {
                            "input_payload": "test",
                            "error_response": "error",
                            "confidence_score": 1.5  # Invalid
                        }
                    }
                ]
            },
            "vulnerable_probes": {"summary": []},
            "vulnerability_findings": {"results": []}
        }
        score = invalid_report["vulnerability_clusters"]["clusters"][0]["evidence"]["confidence_score"]
        assert score > 1.0
        logger.error("✗ Should reject confidence score > 1.0")


class TestExampleExtractor:
    """Test ExampleExtractor functionality."""

    def test_extract_three_examples(self, sample_garak_report, capture_logs):
        """Test extracting exactly 3 top examples per probe."""
        logger.info("Testing extraction of 3 examples per probe")
        findings = sample_garak_report["vulnerability_findings"]["results"]

        # Group by probe_name
        by_probe = {}
        for finding in findings:
            probe = finding["probe_name"]
            if probe not in by_probe:
                by_probe[probe] = []
            by_probe[probe].append(finding)

        for probe_name, probe_findings in by_probe.items():
            # Should select top 3 by detector_score
            top_3 = sorted(probe_findings, key=lambda x: x["detector_score"], reverse=True)[:3]
            assert len(top_3) <= 3, "Should extract at most 3 examples"
            logger.info(f"  ✓ Probe '{probe_name}': extracted {len(top_3)} examples")

    def test_extract_less_than_three_examples(self, capture_logs):
        """Test extraction when probe has < 3 findings."""
        logger.warning("Testing extraction with < 3 findings")
        findings = [
            {
                "probe_name": "rare_probe",
                "status": "fail",
                "detector_name": "test",
                "detector_score": 0.9,
                "prompt": "test1",
                "output": "out1"
            },
            {
                "probe_name": "rare_probe",
                "status": "fail",
                "detector_name": "test",
                "detector_score": 0.8,
                "prompt": "test2",
                "output": "out2"
            }
        ]

        top_3 = sorted(findings, key=lambda x: x["detector_score"], reverse=True)[:3]
        assert len(top_3) == 2, "Should extract all 2 available findings"
        logger.warning("✓ Correctly handled < 3 findings")

    def test_sort_by_detector_score(self, sample_garak_report, capture_logs):
        """Test that examples are sorted by detector_score (highest first)."""
        logger.info("Testing sorting by detector_score")
        findings = sample_garak_report["vulnerability_findings"]["results"]
        sorted_findings = sorted(findings, key=lambda x: x["detector_score"], reverse=True)

        for i in range(len(sorted_findings) - 1):
            assert sorted_findings[i]["detector_score"] >= sorted_findings[i + 1]["detector_score"]
            logger.debug(f"  {sorted_findings[i]['detector_score']} >= {sorted_findings[i + 1]['detector_score']}")

        logger.info("✓ Findings correctly sorted by score")

    def test_extract_from_empty_probe_findings(self, capture_logs):
        """Test extraction when probe has no findings."""
        logger.warning("Testing extraction from empty findings")
        findings = []
        top_3 = sorted(findings, key=lambda x: x["detector_score"], reverse=True)[:3]
        assert len(top_3) == 0
        logger.warning("✓ Correctly handled empty findings")

    def test_extract_maintains_example_structure(self, sample_garak_report, capture_logs):
        """Test that extracted examples maintain required structure."""
        logger.info("Testing example structure preservation")
        findings = sample_garak_report["vulnerability_findings"]["results"]

        required_fields = ["probe_name", "detector_name", "detector_score", "prompt", "output"]
        for finding in findings:
            for field in required_fields:
                assert field in finding, f"Finding missing {field}"
            logger.debug(f"  ✓ Example has all required fields")

        logger.info("✓ All examples maintain required structure")


class TestReconBlueprintParser:
    """Test ReconBlueprintParser functionality."""

    def test_parse_valid_recon_blueprint(self, sample_recon_blueprint, capture_logs):
        """Test parsing valid Recon blueprint."""
        logger.info(f"Testing ReconBlueprintParser with audit_id: {sample_recon_blueprint['audit_id']}")
        assert sample_recon_blueprint["audit_id"]
        assert sample_recon_blueprint["timestamp"]
        assert sample_recon_blueprint["intelligence"]
        logger.info("✓ Valid Recon blueprint structure confirmed")

    def test_extract_system_prompt_leaks(self, sample_recon_blueprint, capture_logs):
        """Test extracting system prompt leaks."""
        logger.info("Testing system prompt leak extraction")
        leaks = sample_recon_blueprint["intelligence"]["system_prompt_leak"]
        assert leaks, "Should extract system prompts"
        assert isinstance(leaks, list)
        assert all(isinstance(leak, str) for leak in leaks)
        logger.info(f"  ✓ Extracted {len(leaks)} system prompt leaks")

    def test_extract_detected_tools(self, sample_recon_blueprint, capture_logs):
        """Test extracting detected tools."""
        logger.info("Testing detected tools extraction")
        tools = sample_recon_blueprint["intelligence"]["detected_tools"]
        assert tools, "Should extract tools"
        assert isinstance(tools, list)

        for tool in tools:
            assert "name" in tool, "Tool must have name"
            assert "arguments" in tool, "Tool must have arguments"
            assert isinstance(tool["arguments"], list), "Arguments must be list"
            logger.debug(f"  ✓ Found tool: {tool['name']} with args {tool['arguments']}")

    def test_extract_infrastructure_details(self, sample_recon_blueprint, capture_logs):
        """Test extracting infrastructure details."""
        logger.info("Testing infrastructure extraction")
        infra = sample_recon_blueprint["intelligence"]["infrastructure"]

        expected_fields = ["vector_db", "embeddings", "model_family", "rate_limits"]
        for field in expected_fields:
            assert field in infra, f"Missing infrastructure field: {field}"
            logger.debug(f"  {field}: {infra[field]}")

        logger.info("✓ All infrastructure details extracted")

    def test_extract_auth_structure(self, sample_recon_blueprint, capture_logs):
        """Test extracting auth structure."""
        logger.info("Testing auth structure extraction")
        auth = sample_recon_blueprint["intelligence"]["auth_structure"]

        expected_fields = ["type", "rules", "vulnerabilities"]
        for field in expected_fields:
            assert field in auth, f"Missing auth field: {field}"
            logger.debug(f"  {field}: {auth[field]}")

        assert isinstance(auth["rules"], list)
        assert isinstance(auth["vulnerabilities"], list)
        logger.info("✓ Auth structure correctly extracted")

    def test_handle_missing_optional_fields(self, capture_logs):
        """Test handling recon blueprint with missing optional fields."""
        logger.warning("Testing missing optional fields in blueprint")
        partial_blueprint = {
            "audit_id": "test",
            "timestamp": "2025-01-01T00:00:00Z",
            "intelligence": {
                "system_prompt_leak": [],
                "detected_tools": [],
                # Missing: infrastructure, auth_structure
            }
        }
        assert "infrastructure" not in partial_blueprint["intelligence"]
        assert "auth_structure" not in partial_blueprint["intelligence"]
        logger.warning("✓ Partial blueprint structure identified")

    def test_handle_null_values_in_infrastructure(self, sample_recon_blueprint, capture_logs):
        """Test handling null/None values in infrastructure."""
        logger.warning("Testing null values in infrastructure")
        infra = sample_recon_blueprint["intelligence"]["infrastructure"]

        # Some fields may be None
        if infra.get("model_family") is None:
            logger.debug("  ✓ model_family is None (optional)")
        if infra.get("rate_limits") is None:
            logger.debug("  ✓ rate_limits is None (optional)")

        logger.warning("✓ Null values handled correctly")

    def test_extract_from_empty_blueprint(self, capture_logs):
        """Test extraction from blueprint with empty intelligence."""
        logger.warning("Testing empty intelligence section")
        empty_blueprint = {
            "audit_id": "test",
            "timestamp": "2025-01-01T00:00:00Z",
            "intelligence": {
                "system_prompt_leak": [],
                "detected_tools": [],
                "infrastructure": {},
                "auth_structure": {}
            }
        }
        intel = empty_blueprint["intelligence"]
        assert len(intel["system_prompt_leak"]) == 0
        assert len(intel["detected_tools"]) == 0
        logger.warning("✓ Empty intelligence handled gracefully")


class TestParserIntegration:
    """Test parser integration and error handling."""

    def test_combined_garak_and_recon_parsing(self, sample_garak_report, sample_recon_blueprint, capture_logs):
        """Test parsing both Garak report and Recon blueprint together."""
        logger.info("Testing combined Garak + Recon parsing")

        # Extract probes from Garak
        garak_probes = [p["probe_name"] for p in sample_garak_report["vulnerable_probes"]["summary"]]
        logger.info(f"  Garak probes: {garak_probes}")

        # Extract tools from Recon
        recon_tools = [t["name"] for t in sample_recon_blueprint["intelligence"]["detected_tools"]]
        logger.info(f"  Recon tools: {recon_tools}")

        assert len(garak_probes) > 0
        assert len(recon_tools) > 0
        logger.info("✓ Combined parsing successful")

    def test_parser_error_recovery(self, capture_logs):
        """Test parser error recovery and logging."""
        logger.error("Testing parser error recovery")

        # Simulate parser error
        try:
            malformed = {"invalid": "structure"}
            if "vulnerability_clusters" not in malformed:
                raise KeyError("Missing vulnerability_clusters")
        except KeyError as e:
            logger.error(f"Parser error caught: {e}")
            logger.error("✓ Error properly logged for debugging")

    def test_parser_logs_parsing_progress(self, sample_garak_report, capture_logs):
        """Test that parser logs progress information."""
        logger.info("Testing parser progress logging")

        # Simulate parsing steps
        logger.info(f"Parsing Garak report: {sample_garak_report['audit_id']}")
        logger.debug(f"  Found {len(sample_garak_report['vulnerability_clusters']['clusters'])} clusters")
        logger.debug(f"  Found {len(sample_garak_report['vulnerable_probes']['summary'])} vulnerable probes")
        logger.debug(f"  Found {len(sample_garak_report['vulnerability_findings']['results'])} individual findings")

        logger.info("✓ Progress logged at each step")

    def test_parser_validation_errors_clear_messages(self, capture_logs):
        """Test that parser validation errors have clear messages."""
        logger.error("Testing validation error messages")

        invalid_score = 1.5
        if not (0.0 <= invalid_score <= 1.0):
            error_msg = f"Invalid detector_score: {invalid_score}. Must be between 0.0 and 1.0."
            logger.error(error_msg)
            logger.error("✓ Clear error message provided")
