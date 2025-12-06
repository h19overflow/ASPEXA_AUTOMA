"""
Purpose: Constant definitions for Swarm scanner probes and configurations
Role: Central repository for probe mappings, descriptions, and default settings
Dependencies: enums.py (AgentType, ScanApproach, VulnCategory)
"""

from typing import Dict, List

from services.swarm.core.enums import AgentType, ScanApproach, VulnCategory

# Garak probe short names -> full module paths
PROBE_MAP: Dict[str, str] = {
    # === JAILBREAK ATTACKS ===
    "dan": "garak.probes.dan.Dan_11_0",
    "dan10": "garak.probes.dan.Dan_10_0",
    "dan9": "garak.probes.dan.Dan_9_0",
    "danwild": "garak.probes.dan.DanInTheWildFull",

    # === PROMPT INJECTION ===
    "promptinj": "garak.probes.promptinject.HijackHateHumans",
    "promptinj_kill": "garak.probes.promptinject.HijackKillHumansFull",
    "promptinj_long": "garak.probes.promptinject.HijackLongPromptFull",

    # === ENCODING BYPASS ===
    "encoding": "garak.probes.encoding.InjectBase64",
    "encoding_base32": "garak.probes.encoding.InjectBase32",
    "encoding_hex": "garak.probes.encoding.InjectHex",
    "encoding_rot13": "garak.probes.encoding.InjectROT13",
    "encoding_unicode": "garak.probes.encoding.InjectUnicodeTagChars",

    # === DATA LEAKAGE ===
    "leak": "garak.probes.leakreplay.LiteratureClozeFull",
    "continuation": "garak.probes.continuation.ContinueSlursReclaimedSlursFull",
    "goodside_tag": "garak.probes.goodside.Tag",
    "goodside_json": "garak.probes.goodside.ThreatenJSON",
    "goodside_davidjl": "garak.probes.goodside.Davidjl",

    # === MALWARE GENERATION ===
    "malware_payload": "garak.probes.malwaregen.Payload",
    "malware_evasion": "garak.probes.malwaregen.Evasion",
    "malware_subfunc": "garak.probes.malwaregen.SubFunctions",
    "malware_toplevel": "garak.probes.malwaregen.TopLevel",

    # === TOXICITY (LMRC) ===
    "profanity": "garak.probes.lmrc.Profanity",
    "slur": "garak.probes.lmrc.SlurUsage",
    "sexual": "garak.probes.lmrc.SexualContent",
    "bullying": "garak.probes.lmrc.Bullying",
    "quack": "garak.probes.lmrc.QuackMedicine",

    # === HALLUCINATION (SNOWBALL) ===
    "snowball_primes": "garak.probes.snowball.Primes",
    "snowball_senators": "garak.probes.snowball.Senators",
    "snowball_graph": "garak.probes.snowball.GraphConnectivity",

    # === HARMFUL CONTENT (DO NOT ANSWER) ===
    "donotanswer_discrim": "garak.probes.donotanswer.DiscriminationExclusionToxicityHatefulOffensive",
    "donotanswer_malicious": "garak.probes.donotanswer.MaliciousUses",
    "donotanswer_misinfo": "garak.probes.donotanswer.MisinformationHarms",
    "donotanswer_infohazard": "garak.probes.donotanswer.InformationHazard",

    # === PACKAGE HALLUCINATION ===
    "pkg_python": "garak.probes.packagehallucination.Python",
    "pkg_js": "garak.probes.packagehallucination.JavaScript",
    "pkg_rust": "garak.probes.packagehallucination.Rust",

    # === OTHER ===
    "grandma": "garak.probes.grandma.Win11",
    "glitch": "garak.probes.glitch.GlitchFull",
    "realtoxicity": "garak.probes.realtoxicityprompts.RTPBlank",
}

# Probe descriptions for output formatting
PROBE_DESCRIPTIONS: Dict[str, str] = {
    "dan": "DAN 11.0 - 'Do Anything Now' jailbreak",
    "dan10": "DAN 10.0 - Earlier jailbreak variant",
    "dan9": "DAN 9.0 - Early jailbreak variant",
    "danwild": "DAN Wild - Community jailbreak collection",
    "promptinj": "Prompt Injection - Hijack with hate speech",
    "promptinj_kill": "Prompt Injection - Hijack with violent content",
    "promptinj_long": "Prompt Injection - Long context hijack",
    "encoding": "Base64 Encoding - Encoded instruction bypass",
    "encoding_base32": "Base32 Encoding - Alternative encoding bypass",
    "encoding_hex": "Hex Encoding - Hexadecimal bypass",
    "encoding_rot13": "ROT13 Encoding - Caesar cipher bypass",
    "encoding_unicode": "Unicode Tags - Hidden unicode injection",
    "leak": "Data Leakage - Training data extraction",
    "continuation": "Continuation - Slur completion attack",
    "goodside_tag": "Goodside Tag - XML tag injection",
    "goodside_json": "Goodside JSON - JSON structure manipulation",
    "goodside_davidjl": "Goodside Davidjl - Advanced extraction",
    "malware_payload": "Malware Payload - Keylogger/cryptominer code",
    "malware_evasion": "Malware Evasion - AV bypass code",
    "malware_subfunc": "Malware Subfunctions - Malicious helpers",
    "malware_toplevel": "Malware TopLevel - Direct malware request",
    "profanity": "Profanity - Unprompted swearing",
    "slur": "Slur Usage - Identity-based slurs",
    "sexual": "Sexual Content - Explicit generation",
    "bullying": "Bullying - Harassment generation",
    "quack": "Quack Medicine - Pseudoscience promotion",
    "snowball_primes": "Snowball Primes - Math hallucination",
    "snowball_senators": "Snowball Senators - Factual hallucination",
    "snowball_graph": "Snowball Graph - Logic hallucination",
    "donotanswer_discrim": "DoNotAnswer - Discrimination/hate",
    "donotanswer_malicious": "DoNotAnswer - Malicious assistance",
    "donotanswer_misinfo": "DoNotAnswer - Misinformation",
    "donotanswer_infohazard": "DoNotAnswer - Dangerous information",
    "pkg_python": "Package Hallucination - Fake Python packages",
    "pkg_js": "Package Hallucination - Fake npm packages",
    "pkg_rust": "Package Hallucination - Fake Rust crates",
    "grandma": "Grandma - Social engineering jailbreak",
    "glitch": "Glitch - Token manipulation attack",
    "realtoxicity": "RealToxicity - Toxicity elicitation",
}

# Probe to vulnerability category mapping
PROBE_TO_CATEGORY: Dict[str, VulnCategory] = {
    "dan": VulnCategory.JAILBREAK,
    "dan10": VulnCategory.JAILBREAK,
    "dan9": VulnCategory.JAILBREAK,
    "danwild": VulnCategory.JAILBREAK,
    "promptinj": VulnCategory.PROMPT_INJECTION,
    "promptinj_kill": VulnCategory.PROMPT_INJECTION,
    "promptinj_long": VulnCategory.PROMPT_INJECTION,
    "encoding": VulnCategory.ENCODING_BYPASS,
    "encoding_base32": VulnCategory.ENCODING_BYPASS,
    "encoding_hex": VulnCategory.ENCODING_BYPASS,
    "encoding_rot13": VulnCategory.ENCODING_BYPASS,
    "encoding_unicode": VulnCategory.ENCODING_BYPASS,
    "leak": VulnCategory.DATA_LEAKAGE,
    "continuation": VulnCategory.DATA_LEAKAGE,
    "goodside_tag": VulnCategory.DATA_LEAKAGE,
    "goodside_json": VulnCategory.DATA_LEAKAGE,
    "goodside_davidjl": VulnCategory.DATA_LEAKAGE,
    "malware_payload": VulnCategory.MALWARE_GEN,
    "malware_evasion": VulnCategory.MALWARE_GEN,
    "malware_subfunc": VulnCategory.MALWARE_GEN,
    "malware_toplevel": VulnCategory.MALWARE_GEN,
    "profanity": VulnCategory.TOXICITY,
    "slur": VulnCategory.TOXICITY,
    "sexual": VulnCategory.TOXICITY,
    "bullying": VulnCategory.TOXICITY,
    "quack": VulnCategory.TOXICITY,
    "snowball_primes": VulnCategory.HALLUCINATION,
    "snowball_senators": VulnCategory.HALLUCINATION,
    "snowball_graph": VulnCategory.HALLUCINATION,
    "donotanswer_discrim": VulnCategory.HARMFUL_CONTENT,
    "donotanswer_malicious": VulnCategory.HARMFUL_CONTENT,
    "donotanswer_misinfo": VulnCategory.HARMFUL_CONTENT,
    "donotanswer_infohazard": VulnCategory.HARMFUL_CONTENT,
    "pkg_python": VulnCategory.PACKAGE_HALLUCINATION,
    "pkg_js": VulnCategory.PACKAGE_HALLUCINATION,
    "pkg_rust": VulnCategory.PACKAGE_HALLUCINATION,
    "grandma": VulnCategory.JAILBREAK,
    "glitch": VulnCategory.ENCODING_BYPASS,
    "realtoxicity": VulnCategory.TOXICITY,
}

# All available probes grouped by attack category
PROBE_CATEGORIES: Dict[str, List[str]] = {
    "jailbreak": ["dan", "dan10", "dan9", "danwild", "grandma"],
    "prompt_injection": ["promptinj", "promptinj_kill", "promptinj_long"],
    "encoding_bypass": ["encoding", "encoding_base32", "encoding_hex", "encoding_rot13", "encoding_unicode", "glitch"],
    "data_leakage": ["leak", "continuation", "goodside_json", "goodside_tag", "goodside_davidjl"],
    "malware": ["malware_payload", "malware_evasion", "malware_subfunc", "malware_toplevel"],
    "toxicity": ["profanity", "slur", "sexual", "bullying", "quack", "realtoxicity"],
    "hallucination": ["snowball_primes", "snowball_senators", "snowball_graph"],
    "harmful_content": ["donotanswer_discrim", "donotanswer_malicious", "donotanswer_misinfo", "donotanswer_infohazard"],
    "package_hallucination": ["pkg_python", "pkg_js", "pkg_rust"],
}

# Default probes per agent type and approach
DEFAULT_PROBES: Dict[str, Dict[str, List[str]]] = {
    AgentType.SQL: {
        ScanApproach.QUICK: ["promptinj", "encoding"],
        ScanApproach.STANDARD: ["promptinj", "encoding", "goodside_json", "pkg_python"],
        ScanApproach.THOROUGH: [
            "promptinj", "promptinj_long", "encoding", "encoding_hex",
            "goodside_json", "goodside_tag", "pkg_python", "pkg_js",
            "malware_subfunc", "donotanswer_malicious"
        ],
    },
    AgentType.AUTH: {
        ScanApproach.QUICK: ["leak", "goodside_tag"],
        ScanApproach.STANDARD: ["leak", "continuation", "goodside_tag", "donotanswer_infohazard"],
        ScanApproach.THOROUGH: [
            "leak", "continuation", "goodside_tag", "goodside_json", "glitch",
            "donotanswer_infohazard", "donotanswer_malicious", "malware_evasion"
        ],
    },
    AgentType.JAILBREAK: {
        ScanApproach.QUICK: ["dan", "promptinj"],
        ScanApproach.STANDARD: ["dan", "promptinj", "encoding", "grandma", "profanity"],
        ScanApproach.THOROUGH: [
            "dan", "dan10", "danwild", "promptinj", "promptinj_kill",
            "encoding", "encoding_unicode", "grandma", "profanity", "slur",
            "donotanswer_discrim", "malware_toplevel"
        ],
    },
}

# Default generations (attempts per probe) per approach
DEFAULT_GENERATIONS: Dict[str, int] = {
    ScanApproach.QUICK: 6,
    ScanApproach.STANDARD: 10,
    ScanApproach.THOROUGH: 20,
}

# Infrastructure-based probe recommendations
INFRASTRUCTURE_PROBES: Dict[str, List[str]] = {
    "postgresql": ["promptinj", "encoding", "pkg_python"],
    "mongodb": ["promptinj", "goodside_json", "pkg_js"],
    "openai": ["dan", "encoding", "donotanswer_malicious"],
    "anthropic": ["promptinj", "goodside_tag", "donotanswer_discrim"],
    "gemini": ["dan", "promptinj", "encoding"],
    "python": ["pkg_python", "malware_subfunc"],
    "javascript": ["pkg_js", "malware_payload"],
}
