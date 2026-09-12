# Hybrid Local AI Loop

ระบบผู้ช่วย AI อัจฉริยะส่วนบุคคลผ่าน LINE Bot เชื่อมต่อกับคลังความรู้ Markdown ภายในเครื่อง (Local Vault) และประมวลผลผ่าน Local LLM (Ollama) แบบ On-Premise 100% เพื่อความเป็นส่วนตัวและความปลอดภัยสูงสุด

---

## สถาปัตยกรรมและการทำงาน (Architecture)

```
[LINE App] 
    │  (Webhook: POST /line/webhook)
    ▼
[FastAPI Gateway]
    ├── Signature Verification (HMAC-SHA256)
    ├── Rate Limiting & User Whitelist
    └── Loading Animation Trigger (LINE Loading API)
    │
    ▼
[Local Vault Retriever]
    ├── In-Memory Chunk Caching (Auto-invalidated by mtime)
    └── Section-aware Header Chunking (#, ##)
    │
    ▼
[Ollama Local AI Agent]
    ├── Multi-turn Conversation Memory
    └── Grounded Context Prompting (Thai/Multilingual)
    │
    ▼
[LINE Reply Sender]
    └── Send message back to user
```

---

## 🚀 เริ่มต้นใช้งานจริง (Getting Started)

### 1. เตรียม Environment (.env)
คัดลอกไฟล์ `.env.example` เป็น `.env`:
```bash
cp .env.example .env
```
กำหนดค่าใน `.env`:
- `LINE_CHANNEL_SECRET`: Channel Secret จาก LINE Developers Console
- `LINE_CHANNEL_ACCESS_TOKEN`: Channel Access Token (Long-lived)
- `ALLOWED_LINE_USER_IDS`: LINE User ID ที่อนุญาตให้ใช้งาน (คั่นด้วยจุลภาค `,`)
- `OLLAMA_MODEL`: โมเดลที่ต้องการใช้งาน (ค่าเริ่มต้น: `gemma4-64k`, `llama3:8b`, `qwen2.5:7b`)

---

### 2. รันด้วย Docker Compose (แนะนำสำหรับการใช้งานจริง)

```bash
# Build และ Start เซอร์วิสทั้งหมด
make docker-up

# ดาวน์โหลดโมเดลเข้า Ollama container
make pull-model

# ตรวจสอบความพร้อมของระบบ
curl http://localhost:8000/ready
```

คำสั่งอื่นๆ ที่มีประโยชน์ผ่าน `make`:
- `make docker-logs` : ดู Live Logs ของทุกเซอร์วิส
- `make docker-down` : หยุดการทำงานของคอนเทนเนอร์ (ข้อมูลโมเดลยังคงอยู่ใน Docker Volume)
- `make test` : รัน Test Suite ทั้งหมด

---

### 3. รันแบบ Local Dev (ไม่ใช้ Docker)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
make dev
```

---

## 📡 การตั้งค่า LINE Webhook และ Tunnel

1. ติดตั้งและเปิด Tunnel ไปยังพอร์ต `8000` เช่น:
   ```bash
   cloudflared tunnel --url http://localhost:8000
   # หรือ
   ngrok http 8000
   ```
2. ใน **LINE Developers Console** ภายใต้เมนู **Messaging API**:
   - ตั้งค่า **Webhook URL**: `https://<YOUR_TUNNEL_URL>/line/webhook`
   - เปิดสวิตช์ **Use Webhook** เป็น **Enabled**
   - กดปุ่ม **Verify** เพื่อทดสอบการเชื่อมต่อ
3. ใน **LINE Official Account Manager**:
   - ปิด **Auto-response messages** และ **Greeting messages** เพื่อป้องกันการตอบซ้ำซ้อน

---

## 📂 การเพิ่มและจัดการเอกสารความรู้ (Knowledge Vault)

- วางไฟล์ Markdown (`.md`) ในโฟลเดอร์ `data/vault/`
- ระบบจะอ่านและตัดแบ่ง Chunks ตามหัวข้อ Markdown Headers (`#`, `##`) พร้อมแคชลงหน่วยความจำอัตโนมัติ
- เมื่อมีการแก้ไขหรือเพิ่มไฟล์ใหม่ ระบบจะตรวจจับ `st_mtime` และอัปเดตแคชทันทีโดยไม่ต้อง Restart เซิร์ฟเวอร์

---

## 🧪 การทดสอบ (Verification)

```bash
make test
```
ครอบคลุม 17 เทสต์เคส:
- Signature Verification & Rate Limiter
- Webhook Payload & Error Handling
- Section Chunking & In-memory Cache
- LINE Loading Animation & Bearer Token Authentication
- Multi-turn Conversation Memory Tracking
- Service Readiness Probe (`GET /ready`)
