import os
os.environ.setdefault("FLAGS_enable_pir_api", "0")
os.environ.setdefault("FLAGS_use_mkldnn", "0")
from paddleocr import PaddleOCR
import paddle
import paddleocr
print("paddle:", paddle.__version__)
print("paddleocr:", paddleocr.__version__)
ocr = PaddleOCR(
    lang="ru",
    text_detection_model_name="PP-OCRv5_mobile_det",
    text_recognition_model_name="eslav_PP-OCRv5_mobile_rec",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    engine="paddle",
    enable_mkldnn=False,
)
print("OCR_INIT_OK")
