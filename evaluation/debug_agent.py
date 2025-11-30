import sys
import os
import asyncio

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import agent

async def debug():
    print("Running agent...")
    try:
        # Run a simple query
        handler = agent.run("What is the signature of 'png_get_cHRM'?")
        response = await handler
        
        print(f"\nType of response: {type(response)}")
        print(f"Dir of response: {dir(response)}")
        
        if hasattr(response, 'response'):
            print(f"\nresponse.response: {response.response}")
        
        try:
            print(f"\nstr(response): {str(response)}")
        except Exception as e:
            print(f"\nstr(response) failed: {e}")
            
    except Exception as e:
        print(f"Agent run failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug())
