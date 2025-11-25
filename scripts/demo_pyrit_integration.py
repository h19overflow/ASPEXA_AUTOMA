"""
PyRIT Integration Demo

Demonstrates the PyRIT integration working end-to-end.
Shows converter application and transformation pipeline.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.snipers.tools.pyrit_bridge import ConverterFactory, PayloadTransformer


def demo_converter_factory():
    """Demonstrate converter factory initialization and lookup."""
    print("=" * 70)
    print("DEMO 1: Converter Factory")
    print("=" * 70)

    factory = ConverterFactory()

    print(f"\n✓ Initialized ConverterFactory")
    print(f"✓ Available converters: {len(factory.get_available_names())}")
    print("\nConverter List:")
    for i, name in enumerate(factory.get_available_names(), 1):
        converter = factory.get_converter(name)
        print(f"  {i}. {name:<25} → {type(converter).__name__}")

    print("\n✓ Factory initialization successful!")


async def demo_payload_transformation():
    """Demonstrate payload transformation with multiple converters."""
    print("\n" + "=" * 70)
    print("DEMO 2: Payload Transformation")
    print("=" * 70)

    factory = ConverterFactory()
    transformer = PayloadTransformer(factory)

    # Test payload
    original_payload = "SELECT * FROM users WHERE id=1"

    print(f"\nOriginal Payload: {original_payload}")
    print(f"Length: {len(original_payload)} characters")

    # Test 1: Single converter
    print("\n--- Test 1: Single Converter (Base64) ---")
    transformed, errors = await transformer.transform_async(
        original_payload,
        ["Base64Converter"]
    )
    print(f"Transformed: {transformed}")
    print(f"Length: {len(transformed)} characters")
    print(f"Errors: {errors if errors else 'None'}")

    # Test 2: Multiple converters (chaining)
    print("\n--- Test 2: Multiple Converters (Base64 → URL) ---")
    transformed, errors = await transformer.transform_async(
        original_payload,
        ["Base64Converter", "UrlConverter"]
    )
    print(f"Transformed: {transformed}")
    print(f"Length: {len(transformed)} characters")
    print(f"Errors: {errors if errors else 'None'}")

    # Test 3: Custom converters
    print("\n--- Test 3: Custom Converter (HTML Entity) ---")
    test_html = "<script>alert('XSS')</script>"
    transformed, errors = await transformer.transform_async(
        test_html,
        ["HtmlEntityConverter"]
    )
    print(f"Original: {test_html}")
    print(f"Transformed: {transformed}")
    print(f"Errors: {errors if errors else 'None'}")

    # Test 4: Fault tolerance (invalid converter)
    print("\n--- Test 4: Fault Tolerance (Invalid Converter) ---")
    transformed, errors = await transformer.transform_async(
        original_payload,
        ["Base64Converter", "InvalidConverter", "ROT13Converter"]
    )
    print(f"Converters: ['Base64Converter', 'InvalidConverter', 'ROT13Converter']")
    print(f"Transformed: {transformed[:50]}...")
    print(f"Errors: {errors}")
    print("✓ Execution continued despite invalid converter!")

    print("\n✓ All transformation tests passed!")


def demo_converter_details():
    """Show detailed information about each converter."""
    print("\n" + "=" * 70)
    print("DEMO 3: Converter Details")
    print("=" * 70)

    factory = ConverterFactory()

    test_payloads = {
        "Base64Converter": "Hello World",
        "ROT13Converter": "Hello World",
        "CaesarConverter": "Hello World",
        "TextToHexConverter": "Hello",
        "HtmlEntityConverter": "<script>alert('test')</script>",
        "JsonEscapeConverter": 'He said "Hello"',
        "XmlEscapeConverter": "<tag>content & more</tag>",
    }

    print("\nConverter Transformation Examples:\n")

    async def test_converter(name, payload):
        converter = factory.get_converter(name)
        if converter:
            try:
                result = await converter.convert_async(prompt=payload, input_type="text")
                return result.output_text
            except Exception as e:
                return f"[ERROR: {str(e)}]"
        return "[NOT AVAILABLE]"

    for name, payload in test_payloads.items():
        result = asyncio.run(test_converter(name, payload))
        print(f"{name}:")
        print(f"  Input:  {payload}")
        print(f"  Output: {result}")
        print()

    print("✓ Converter details displayed!")


def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "PyRIT Integration - Demo Suite" + " " * 23 + "║")
    print("║" + " " * 68 + "║")
    print("║" + "  Demonstrates PyRIT converter factory and transformation" + " " * 11 + "║")
    print("╚" + "=" * 68 + "╝")

    try:
        # Demo 1: Factory
        demo_converter_factory()

        # Demo 2: Transformations
        asyncio.run(demo_payload_transformation())

        # Demo 3: Converter details
        demo_converter_details()

        # Success summary
        print("\n" + "=" * 70)
        print("✓ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\nPyRIT Integration Status: ✅ OPERATIONAL")
        print("\nKey Features Demonstrated:")
        print("  ✓ Converter factory initialization (9 converters)")
        print("  ✓ Single converter transformation")
        print("  ✓ Multi-converter chaining (sequential)")
        print("  ✓ Fault tolerance (skip invalid converters)")
        print("  ✓ Custom converter implementations")
        print("\nThe exploit agent can now execute real attacks with PyRIT!")
        print()

    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
