import asyncio
import os
import sys
sys.path.append(os.getcwd())

from teacher_engine import build_answer
print('Testing build_answer()...')
ans, src = build_answer('Test question for chat', [{'text':'Chunk text','filename':'a.pdf','page':1}], False)
print('ANS:', ans)
print('SRC:', src)

# Now test main.chat by monkeypatching session_exists and search
import main
main.session_exists = lambda s: True
main.search = lambda session_id, question, k: ([{'text':'Chunk text','filename':'a.pdf','page':1}], False)

print('\nTesting main.chat() (monkeypatched session/search)...')

async def run_chat():
    try:
        resp = await main.chat(main.ChatRequest(session_id='dummy', question='Hello'))
        print('CHAT RESP:', resp)
    except Exception as e:
        print('CHAT RAISED:', type(e), e)

asyncio.run(run_chat())
