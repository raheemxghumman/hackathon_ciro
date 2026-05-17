import asyncio
import orchestrator

async def main():
    print("Starting test...")
    await orchestrator.run_pipeline("G-10 mein pani bhar gaya hai gaariyan phans gayi hain")
    print("Done test.")

if __name__ == "__main__":
    asyncio.run(main())
