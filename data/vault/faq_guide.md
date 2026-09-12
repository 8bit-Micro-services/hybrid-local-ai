# คำถามที่พบบ่อย (FAQ) และวิธีแก้ปัญหา

## การตั้งค่า LINE Developers
- **Webhook URL**: ตั้งค่า URL ปลายทางเป็น `https://<YOUR_DOMAIN>/line/webhook`
- **Use Webhook**: เปิดใช้งานเป็น `Enabled`
- **Auto-reply Messages**: ปิด `Auto-response` และ `Greeting messages` ใน LINE Official Account Manager เพื่อไม่ให้ระบบตอบซ้ำซ้อน

## วิธีเพิ่มเอกสารความรู้ใหม่เข้าสู่ระบบ
1. นำไฟล์ Markdown (`.md`) มาวางไว้ในโฟลเดอร์ `data/vault/`
2. ระบบจะทำการตัดแบ่ง Section ตามหัวข้อ `#` หรือ `##` และอัปเดตแคชให้อัตโนมัติทันทีที่มีการแก้ไขไฟล์

## การเปลี่ยนโมเดล Ollama
- แก้ไขตัวแปร `OLLAMA_MODEL` ในไฟล์ `.env` เช่น `gemma4-64k`, `llama3:8b`, หรือ `qwen2.5:7b`
- สั่ง pull โมเดลด้วยคำสั่ง: `ollama pull <model-name>`
