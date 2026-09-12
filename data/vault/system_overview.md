# ภาพรวมระบบ Hybrid Local AI

ระบบ Hybrid Local AI ถูกออกแบบมาสำหรับการประมวลผลคำถาม-ตอบผ่าน LINE Bot โดยประมวลผลภายในเครื่อง (On-Premise / Local) ทั้งหมด 100% เพื่อความเป็นส่วนตัวและความปลอดภัยของข้อมูล

## โครงสร้างระบบ (Architecture)
1. **LINE Webhook Receiver**: รับข้อความและตรวจสอบความถูกต้องของ X-Line-Signature
2. **Local Vault Retriever**: ค้นหาข้อมูลที่เกี่ยวข้องจากไฟล์ Markdown ภายในโฟลเดอร์ `data/vault/`
3. **Ollama AI Agent**: ส่ง Prompt พร้อมบริบท (Context) ไปยัง Local LLM (เช่น Gemma, Llama, Qwen)
4. **LINE Reply Sender**: ส่งคำตอบกลับไปยังผู้ใช้งานผ่าน LINE Messaging API พร้อมระบบแสดงสถานะกำลังพิมพ์ (Loading indicator)

## คุณสมบัติหลัก
- **ความเป็นส่วนตัว**: ข้อมูลเอกสารและประวัติการถามตอบจะไม่ถูกส่งออกไปยัง Cloud LLM ภายนอก
- **ความเสถียร**: มีระบบ Rate Limiting, Error Handling, Memory แคช และ Fallback message เมื่อระบบไม่พร้อมใช้งาน
