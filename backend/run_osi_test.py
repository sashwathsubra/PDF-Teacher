import os
from dotenv import load_dotenv
load_dotenv()
import teacher_engine as te

osi_text = '''**OSI Model Overview**
The OSI model is a seven-layer conceptual framework that standardizes network communication functions. It provides a structured approach to understanding network communication, enabling interoperability, easier troubleshooting, and modular protocol development across diverse networking technologies and vendors.

**The Seven Layers and Their Functions:**
1. **Physical Layer:** Transmits raw bits over a physical medium; defines voltage levels, cabling, and data rates.
2. **Data Link Layer:** Provides framing, physical addressing (MAC), and error detection between directly connected nodes.
3. **Network Layer:** Handles logical addressing (IP) and routing of packets across different networks.
4. **Transport Layer:** Ensures reliable end-to-end data delivery, flow control, and error recovery using protocols like TCP and UDP.
5. **Session Layer:** Establishes, manages, and terminates communication sessions between applications.
6. **Presentation Layer:** Handles data translation, encryption, and compression, ensuring compatibility between different systems.
7. **Application Layer:** Provides network services directly to end-user applications like email, file transfer, and web browsing.

**(Source: CN 1 2.pdf, pages 1, 3, and 8)**'''

ans, src = te.build_answer('Explain OSI', [{'text': osi_text, 'filename':'CN 1 2.pdf', 'page':3}], False)
print('ANS:\n')
print(ans)
print('\nSOURCES:\n', src)
