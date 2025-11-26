"""Cartographer service main entry point."""
import os
import asyncio
from dotenv import load_dotenv
from libs.events.publisher import app


# Load environment variables
load_dotenv()

# Verify required environment variables
required_vars = ["GOOGLE_API_KEY", "REDIS_URL"]
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"WARNING: Missing environment variables: {', '.join(missing_vars)}")
    print("Set GOOGLE_API_KEY and REDIS_URL in .env file")


async def main():
    """Run the Cartographer service."""
    print("=" * 60)
    print("🗺️  Cartographer Service Starting...")
    print("=" * 60)
    print(f"Google API Key: {'✓ Set' if os.getenv('GOOGLE_API_KEY') else '✗ Missing'}")
    print(f"Redis URL: {os.getenv('REDIS_URL', 'redis://localhost:6379')}")
    print("=" * 60)
    
    # Start the FastStream app
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
