# Tên các ảnh trung gian mà pipeline trả về (dict tên bước -> ảnh).
# Phải trùng với api.models.DiagnosisStep.Step — test trong api/tests.py kiểm tra.

# Giai đoạn 1: tiền xử lý (preprocessing.py)
RESIZED = 'resized'
DENOISED = 'denoised'
CLAHE = 'clahe'
# Giai đoạn 2: tách phiến lá khỏi nền (segmentation.py)
SATURATION = 'saturation'
LEAF_MASK = 'leaf_mask'
# Giai đoạn 3: tách đốm bệnh (segmentation.py)
ROI = 'roi'
HEALTHY_MASK = 'healthy_mask'
LESION_MASK_RAW = 'lesion_mask_raw'
LESION_MASK = 'lesion_mask'

# Thứ tự hiển thị trên giao diện
ORDER = (
    RESIZED, DENOISED, CLAHE,
    SATURATION, LEAF_MASK,
    ROI, HEALTHY_MASK, LESION_MASK_RAW, LESION_MASK,
)
