from django.db import migrations

# 10 lớp lá cà chua của PlantVillage (raw/color). code = tên thư mục ảnh = nhãn của bộ phân loại.
DISEASES = [
    (
        'Tomato___Bacterial_spot', 'Bệnh đốm vi khuẩn',
        'Do vi khuẩn Xanthomonas spp. Đốm nhỏ màu nâu sẫm đến đen, hình dạng không đều, '
        'thường có quầng vàng; các đốm liên kết làm lá vàng và rụng.',
    ),
    (
        'Tomato___Early_blight', 'Bệnh đốm vòng (úa sớm)',
        'Do nấm Alternaria solani. Đốm nâu sẫm có các vòng đồng tâm, thường có quầng vàng, '
        'xuất hiện trước ở lá già phía dưới.',
    ),
    (
        'Tomato___Late_blight', 'Bệnh mốc sương',
        'Do Phytophthora infestans. Mảng lớn màu xanh xám đến nâu, mép không rõ, lan rất nhanh; '
        'trời ẩm có lớp mốc trắng ở mặt dưới lá.',
    ),
    (
        'Tomato___Leaf_Mold', 'Bệnh mốc lá',
        'Do nấm Passalora fulva. Mặt trên lá có đốm vàng nhạt, mặt dưới có lớp mốc màu xám ô liu đến nâu.',
    ),
    (
        'Tomato___Septoria_leaf_spot', 'Bệnh đốm lá Septoria',
        'Do nấm Septoria lycopersici. Nhiều đốm tròn nhỏ, tâm xám trắng, viền nâu sẫm, '
        'bắt đầu từ lá già phía dưới.',
    ),
    (
        'Tomato___Spider_mites Two-spotted_spider_mite', 'Nhện đỏ hai chấm',
        'Sâu hại (Tetranychus urticae), không phải bệnh. Chấm li ti màu vàng nhạt do chích hút '
        'rải khắp lá, lá bạc màu; mật độ cao có tơ mảnh ở mặt dưới lá.',
    ),
    (
        'Tomato___Target_Spot', 'Bệnh đốm đích',
        'Do nấm Corynespora cassiicola. Đốm nâu có vòng đồng tâm, tâm sáng màu; dễ nhầm với bệnh đốm vòng.',
    ),
    (
        'Tomato___Tomato_Yellow_Leaf_Curl_Virus', 'Bệnh xoăn vàng lá',
        'Do virus TYLCV, bọ phấn trắng truyền. Lá non nhỏ, xoăn mép lên trên, vàng ở mép lá; '
        'triệu chứng lan cả lá, không thành đốm riêng.',
    ),
    (
        'Tomato___Tomato_mosaic_virus', 'Bệnh khảm lá',
        'Do virus ToMV. Lá loang lổ xanh đậm xen xanh nhạt (khảm), có thể nhăn hoặc biến dạng; '
        'triệu chứng lan cả lá, không thành đốm riêng.',
    ),
    (
        'Tomato___healthy', 'Lá khỏe mạnh',
        'Lá xanh đều, không có đốm hay biến màu.',
    ),
]


def seed_diseases(apps, schema_editor):
    Disease = apps.get_model('api', 'Disease')
    for code, name, description in DISEASES:
        Disease.objects.update_or_create(
            code=code,
            defaults={'name': name, 'description': description, 'is_healthy': code == 'Tomato___healthy'},
        )


def unseed_diseases(apps, schema_editor):
    # Lớp đã có kết quả chẩn đoán dùng tới sẽ không xóa được (PROTECT)
    Disease = apps.get_model('api', 'Disease')
    Disease.objects.filter(code__in=[code for code, _, _ in DISEASES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_disease_severity_level_steps'),
    ]

    operations = [
        migrations.RunPython(seed_diseases, unseed_diseases),
    ]
