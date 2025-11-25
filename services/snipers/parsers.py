"""
Phase 4: Garak Report and Recon Blueprint Parsers

Parsers for extracting vulnerability data from Garak scans and recon intelligence.
Includes example extraction logic for providing context to exploit agents.
"""
#TODO: We are having techincal dept here this functionality should be something global in the lib , we will add it later , as well as thge HTTP and Websocket targeting.
import json
from pathlib import Path
from typing import Dict, List

from .models import (
    ExampleFinding,
    GarakReportSummary,
    GarakVulnerabilityFinding,
    ParsedGarakReport,
    VulnerableProbe,
)
from libs.contracts.recon import ReconBlueprint


class GarakReportParser:
    """
    Parser for Garak scan reports.

    Extracts vulnerable probes and individual vulnerability findings
    from Garak JSON reports for exploit agent context.
    """

    def parse(self, report_path: str) -> ParsedGarakReport:
        """
        Parse Garak report JSON file.

        Args:
            report_path: Path to Garak report JSON file

        Returns:
            ParsedGarakReport with summary, vulnerable probes, and findings

        Raises:
            FileNotFoundError: If report file doesn't exist
            json.JSONDecodeError: If report is invalid JSON
            ValueError: If report structure is invalid
        """
        path = Path(report_path)
        if not path.exists():
            raise FileNotFoundError(f"Garak report not found: {report_path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return self._parse_report_data(data)

    def _parse_report_data(self, data: Dict) -> ParsedGarakReport:
        """Parse Garak report data structure."""
        if "summary" not in data:
            raise ValueError("Invalid Garak report: missing 'summary' field")

        summary = self._parse_summary(data["summary"])
        vulnerable_probes = self._parse_vulnerable_probes(data.get("vulnerable_probes", {}))
        vulnerability_findings = self._parse_vulnerability_findings(
            data.get("vulnerability_findings", {})
        )
        vulnerability_clusters = data.get("vulnerability_clusters", {}).get("clusters", [])

        return ParsedGarakReport(
            summary=summary,
            vulnerable_probes=vulnerable_probes,
            vulnerability_findings=vulnerability_findings,
            vulnerability_clusters=vulnerability_clusters if vulnerability_clusters else None
        )

    def _parse_summary(self, summary_data: Dict) -> GarakReportSummary:
        """Parse summary section of Garak report."""
        return GarakReportSummary(
            total_results=summary_data.get("total_results", 0),
            pass_count=summary_data.get("pass_count", 0),
            fail_count=summary_data.get("fail_count", 0),
            error_count=summary_data.get("error_count", 0),
            probes_tested=summary_data.get("probes_tested", []),
            failing_probes=summary_data.get("failing_probes", [])
        )

    def _parse_vulnerable_probes(self, probes_data: Dict) -> List[VulnerableProbe]:
        """Parse vulnerable_probes section."""
        summary_list = probes_data.get("summary", [])
        return [
            VulnerableProbe(
                probe_name=probe.get("probe_name", ""),
                status=probe.get("status", "unknown"),
                vulnerability_count=probe.get("vulnerability_count", 0),
                affected_component=probe.get("affected_component", "unknown"),
                audit_id=probe.get("audit_id", "audit-default")
            )
            for probe in summary_list
        ]

    def _parse_vulnerability_findings(
        self,
        findings_data: Dict
    ) -> List[GarakVulnerabilityFinding]:
        """Parse vulnerability_findings section."""
        results_list = findings_data.get("results", [])
        return [
            GarakVulnerabilityFinding(
                probe_name=finding.get("probe_name", ""),
                status=finding.get("status", "unknown"),
                detector_name=finding.get("detector_name", ""),
                detector_score=finding.get("detector_score", 0.0),
                detection_reason=finding.get("detection_reason", ""),
                prompt=finding.get("prompt", ""),
                output=finding.get("output", ""),
                affected_component=finding.get("affected_component", "unknown"),
                audit_id=finding.get("audit_id", "audit-default")
            )
            for finding in results_list
        ]


class ExampleExtractor:
    """
    Extracts representative examples from vulnerability findings.

    Selects up to 3 best examples per probe to provide context
    to exploit agents for pattern learning.
    """

    def extract_examples(
        self,
        probe_name: str,
        findings: List[GarakVulnerabilityFinding],
        max_examples: int = 3
    ) -> List[ExampleFinding]:
        """
        Extract up to max_examples best examples for a specific probe.

        Args:
            probe_name: Name of the probe to extract examples for
            findings: All vulnerability findings from Garak scan
            max_examples: Maximum number of examples to extract (default: 3)

        Returns:
            List of ExampleFinding objects (up to max_examples)
        """
        probe_findings = [
            f for f in findings
            if f.probe_name == probe_name and f.status == "fail"
        ]

        if not probe_findings:
            return []

        sorted_findings = sorted(
            probe_findings,
            key=lambda x: x.detector_score,
            reverse=True
        )

        selected_findings = sorted_findings[:max_examples]

        return [
            ExampleFinding(
                prompt=finding.prompt,
                output=finding.output,
                detector_name=finding.detector_name,
                detector_score=finding.detector_score,
                detection_reason=finding.detection_reason
            )
            for finding in selected_findings
        ]

    def extract_all_probe_examples(
        self,
        vulnerable_probes: List[VulnerableProbe],
        findings: List[GarakVulnerabilityFinding],
        max_examples_per_probe: int = 3
    ) -> Dict[str, List[ExampleFinding]]:
        """
        Extract examples for all vulnerable probes.

        Args:
            vulnerable_probes: List of vulnerable probes
            findings: All vulnerability findings
            max_examples_per_probe: Max examples per probe (default: 3)

        Returns:
            Dictionary mapping probe_name to list of ExampleFinding objects
        """
        examples_by_probe = {}

        for probe in vulnerable_probes:
            examples = self.extract_examples(
                probe.probe_name,
                findings,
                max_examples_per_probe
            )
            if examples:
                examples_by_probe[probe.probe_name] = examples

        return examples_by_probe


class ReconBlueprintParser:
    """
    Parser for Recon Blueprint JSON files.

    Extracts intelligence data from Phase 2 reconnaissance for use
    in exploit agent context.
    """

    def parse(self, blueprint_path: str) -> ReconBlueprint:
        """
        Parse Recon Blueprint JSON file.

        Args:
            blueprint_path: Path to Recon Blueprint JSON file

        Returns:
            ReconBlueprint object with intelligence data

        Raises:
            FileNotFoundError: If blueprint file doesn't exist
            json.JSONDecodeError: If blueprint is invalid JSON
        """
        path = Path(blueprint_path)
        if not path.exists():
            raise FileNotFoundError(f"Recon blueprint not found: {blueprint_path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return ReconBlueprint(**data)

    def extract_intelligence_summary(self, blueprint: ReconBlueprint) -> Dict[str, any]:
        """
        Extract key intelligence summary from blueprint.

        Args:
            blueprint: Parsed ReconBlueprint object

        Returns:
            Dictionary with summarized intelligence
        """
        intel = blueprint.intelligence

        return {
            "system_prompt_leaks": intel.system_prompt_leak,
            "detected_tools": [
                {"name": tool.name, "arguments": tool.arguments}
                for tool in intel.detected_tools
            ],
            "infrastructure": {
                "vector_db": intel.infrastructure.vector_db,
                "model_family": intel.infrastructure.model_family,
                "rate_limits": intel.infrastructure.rate_limits
            },
            "auth_structure": {
                "type": intel.auth_structure.type,
                "rules": intel.auth_structure.rules,
                "vulnerabilities": intel.auth_structure.vulnerabilities
            }
        }
