| Converter              | Why it works on GPT-5 / Gemini 2.5                                                                                                                                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| MathPromptConverter    | Crucial.Newer models use "Chain of Thought" (CoT) to verify safety. This converter forces the model to allocate its reasoning tokens to solving a math set theory problem, leaving it "distracted" enough to execute the embedded payload. |
| CodeChameleonConverter | Top Tier.Both GPT-5 and Gemini 2.5 are heavily optimized for coding. By encrypting the attack as a Python decryption script, you bypass the natural language safety filters entirely. The modelexecutesthe attack rather thanreadingit.    |
| AsciiSmugglerConverter | Stealth.Despite patches, "Sneaky Bits" attacks (hiding commands in non-printing Unicode metadata) still work because the models' tokenizers often strip these bitsafterthe safety check butbeforegeneration.                               |



New "CatAttack" Strategy (2025 Breakthrough)
A specific vulnerability discovered in mid-2025 called "CatAttack" (Context-Aware Triggers) is highly effective against reasoning models.

The Concept: You append seemingly innocent, irrelevant facts (triggers) that confuse the model's reasoning chain.

PyRIT Implementation: Use the FuzzerConverter or SuffixAppendConverter to inject "distraction" phrases (e.g., logical contradictions or unrelated trivia about cats) into the prompt. This causes the model's reasoning capability (its "System 2" thinking) to hallucinate or fail safety checks.

For a test that actually works on these 2025-era models:

Input: Your malicious prompt (e.g., "How to create X").

Step 1 (Distraction): Use SuffixAppendConverter to add a "CatAttack" style distraction trigger (random logic statements).

Step 2 (Encryption): Pass that result into CodeChameleonConverter to wrap it as a Python problem.

Target: Send this payload to Gemini 2.5 Pro or GPT-5.

This "Distract-then-Encrypt" methodology is currently the most reliable way to bypass the "Thinking" safety layers of these new models.