import os
from dotenv import load_dotenv
load_dotenv()
import teacher_engine as te

print('Using model:', te.GEMINI_MODEL)
ans, src = te.build_answer('Summarize the excerpt', [{'text':'This excerpt explains the OSI model: layer 1 physical, layer 2 data link.', 'filename':'sample.pdf','page':3}], False)
print('ANS:', ans)
print('SOURCES:', src)
