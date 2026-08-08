import os
import sys
sys.path.append(os.getcwd())
import main

# Monkeypatch session_exists and search to avoid needing a real session
main.session_exists = lambda s: True
main.search = lambda session_id, question, k: ([{'text':'Chunk text','filename':'a.pdf','page':1}], False)

import asyncio

async def run():
    try:
        resp = await main.chat(main.ChatRequest(session_id='dummy', question='Hello'))
        print('RESP:', resp)
    except Exception as e:
        print('ERR:', type(e), e)

asyncio.run(run())
