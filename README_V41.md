# v41 — Local OCR

- Replaced cloud OCR with local PaddleOCR.
- Extracts VIN, Russian plate and vehicle year.
- OCR runs in a worker thread to avoid blocking the Telegram event loop.
- Railway Volume `/data` is used for the PaddleX model cache.
- No `OPENAI_API_KEY` or `DEEPSEEK_API_KEY` is needed for vehicle OCR.
- Existing bot/database/Volume logic is preserved.
