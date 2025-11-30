import sys
import os
import asyncio

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import agent

async def test_single_response():
    print("Testing single agent response...")
    try:
        handler = agent.run("What is the signature of 'png_get_cHRM'?")
        response = await handler
        
        print(f"\n=== Response Object ===")
        print(f"Type: {type(response)}")
        print(f"\nAttributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")
        
        # Try to access response
        if hasattr(response, 'response'):
            print(f"\nresponse.response exists: {response.response}")
            print(f"Type: {type(response.response)}")
            
        # Try message
        if hasattr(response, 'message'):
            print(f"\nresponse.message exists")
            msg = response.message
            print(f"Message type: {type(msg)}")
            print(f"Message attributes: {[attr for attr in dir(msg) if not attr.startswith('_')]}")
            
            if hasattr(msg, 'content'):
                print(f"Message.content: {msg.content}")
            if hasattr(msg, 'blocks'):
                print(f"Message.blocks: {msg.blocks}")
                for i, block in enumerate(msg.blocks):
                    print(f"  Block {i}: {block}")
                    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_single_response())
