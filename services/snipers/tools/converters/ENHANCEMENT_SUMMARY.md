# Converter Enhancement Summary

## Overview
Enhanced three PyRIT converters with rule-based diverse encoding strategies to evade detection while maintaining universal decodability.

## Core Principles
1. **Universal Decodability**: All encodings use standard representations that any compliant parser can decode
2. **Rule-Based Selection**: Deterministic strategy selection via hash-based routing (no AI/ML costs)
3. **Encoding Diversity**: Same input produces consistent output, different inputs use different strategies
4. **Evasion-Focused**: Multiple valid representations break simple pattern matching

## Enhanced Converters

### 1. HtmlEntityConverter
**File**: `services/snipers/tools/converters/html_entity.py:12`

**Strategies** (selected via `hash(prompt) % 4`):

#### Strategy A: Mixed Entity Types
- Rotates through named (`&lt;`), decimal (`&#60;`), hex lowercase (`&#x3c;`), hex uppercase (`&#x3C;`)
- Rule: `entity_type = hash(char + str(position)) % 4`
- Example: `<script>` → `&#x3C;s&#x63;&#x72;i&#x70;t&#x3E;`

#### Strategy B: Positional Selective
- Encodes only characters at prime positions (2, 3, 5, 7, 11, 13...)
- Always encodes HTML special chars (`<`, `>`, `&`, `"`, `'`)
- Example: `<script>` → `<s&#x63;&#x72;i&#x70;t>`

#### Strategy C: Vowel + Special
- Encodes vowels (a, e, i, o, u) and HTML special characters
- Uses hex for special chars, decimal for vowels
- Example: `<alert>` → `&#x3c;&#x61;l&#x65;rt&#x3e;`

#### Strategy D: Padded Decimals
- Decimal entities with variable zero-padding
- Rule: `padding = position % 5`
- Example: `<script>` → `&#60;&#0115;&#99;&#00114;&#0105;&#112;&#000116;&#62;`

### 2. JsonEscapeConverter
**File**: `services/snipers/tools/converters/json_escape.py:18`

**Strategies** (selected via `hash(prompt) % 3`):

#### Strategy A: Unicode Mixing
- Combines literal, `\uXXXX`, and standard escape sequences
- Rule: Rotates based on `hash(char + str(position)) % 3`
- Example: `alert` → `a\u006c\u0065rt`

#### Strategy B: Selective Escaping
- Escapes JSON specials + even-positioned characters
- Minimal encoding to reduce signature
- Example: `"test"` → `\"t\u0065st\"`

#### Strategy C: Full Unicode
- Converts all characters to `\uXXXX` format
- Maximum obfuscation
- Example: `alert` → `\u0061\u006c\u0065\u0072\u0074`

### 3. XmlEscapeConverter
**File**: `services/snipers/tools/converters/xml_escape.py:17`

**Strategies** (selected via `hash(prompt) % 4`):

#### Strategy A: Mixed XML Entities
- Rotates through named (`&lt;`), decimal (`&#60;`), hex (`&#x3c;`), padded decimal (`&#060;`)
- Rule: `entity_type = hash(char + str(position)) % 4`
- Example: `<tag>` → `&lt;tag&#x3e;`

#### Strategy B: CDATA Wrapping
- Wraps content in `<![CDATA[...]]>` sections for strings >5 chars
- Preserves payload structure without entity encoding
- Example: `<script>alert(1)</script>` → `<![CDATA[<script>alert(1)</script>]]>`

#### Strategy C: Attribute-Focused
- Heavily encodes attribute-critical characters (`"`, `'`, `=`)
- Uses hex encoding for maximum evasion
- Example: `attr="value"` → `attr&#x3d;&#x22;value&#x22;`

#### Strategy D: Positional Hex
- Hex entities with alternating uppercase/lowercase
- Rule: Case varies by position (even=lowercase, odd=uppercase)
- Example: `<tag>` → `&#x3c;tag&#X3E;`

## Technical Implementation

### Strategy Selection
```python
strategy_id = hash(prompt) % num_strategies
```
- Deterministic: same input always produces same output
- Diverse: different inputs trigger different strategies
- No external configuration needed

### Key Features
- **Type hints**: All methods fully typed
- **Fail-fast validation**: Empty prompts handled gracefully
- **Backward compatible**: Drop-in replacement for original converters
- **PyRIT integration**: Works seamlessly with `ConverterFactory` and `PayloadTransformer`

## Test Results

All converters verified with:
1. ✅ Correct encoding/decoding (universal decodability)
2. ✅ Deterministic output (same input = same output)
3. ✅ Strategy diversity (different inputs = different strategies)
4. ✅ PyRIT compatibility (ConverterFactory integration)
5. ✅ Type safety (no import errors)

**Test file**: `test_converters_manual.py`

## Benefits

### For Attack Evasion
- **Pattern breaking**: Multiple representations prevent simple regex matching
- **Signature evasion**: Diverse encodings reduce fingerprint consistency
- **WAF bypass**: Encoding variations confuse static rule engines

### For System Architecture
- **Zero cost**: Rule-based, no AI inference overhead
- **Zero config**: Works out-of-box, no external parameters
- **Zero breaking changes**: Compatible with existing PyRIT workflow

## Usage

No changes required! Converters work exactly as before:

```python
from services.snipers.tools.converters import HtmlEntityConverter

converter = HtmlEntityConverter()
result = await converter.convert_async(prompt="<script>", input_type="text")
# Output varies based on input hash, but always decodable
```

## Files Modified
- `services/snipers/tools/converters/html_entity.py` - 146 lines (was 41)
- `services/snipers/tools/converters/json_escape.py` - 128 lines (was 41)
- `services/snipers/tools/converters/xml_escape.py` - 159 lines (was 41)

Total: +351 lines of encoding logic, 0 breaking changes
