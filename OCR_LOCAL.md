# Local OCR v41

VIN / госномер / год теперь распознаются локально через PaddleOCR. OpenAI и DeepSeek для OCR не используются.

- PaddlePaddle CPU 3.2.0
- PaddleOCR 3.x, PP-OCRv5/актуальный pipeline
- Russian recognition model (`lang="ru"`)
- 4 image passes: original, enhanced, upper crop, lower crop
- VIN validation: 17 characters, VIN alphabet, conservative OCR correction
- Russian plate pattern validation
- year extraction near `Год выпуска`
- Paddle model cache is placed in `/data/.paddlex` when Railway Volume `/data` exists
- OCR is executed in a worker thread so CPU inference does not block Telegram's async event loop

The first OCR after deployment may download the local models. Subsequent runs use the cached models on the Railway Volume.
