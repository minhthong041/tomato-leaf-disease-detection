"""Khuyến nghị theo từng bệnh (việc 3D của TV3), khóa theo diseases.code.

Khuyến nghị theo IPM: phòng trước (giống, vệ sinh, canh tác), theo dõi, rồi mới dùng thuốc. Không ghi tên
thương mại hay liều; thuốc dùng theo Danh mục thuốc BVTV được phép sử dụng tại Việt Nam, đúng nhãn.

Mỗi bệnh gồm:
- cause: tác nhân gây bệnh (None với lá khỏe)
- advice: khuyến nghị
- sources: nguồn tham khảo, mỗi nguồn là (tiêu đề, URL)
- replaces_severity_advice: True khi khuyến nghị chung theo cấp (severity.IPM_RECOMMENDATIONS) không đúng
  với lớp này, nên trang kết quả chỉ hiện khuyến nghị theo bệnh: bệnh virus (không có thuốc chữa,
  "phun thuốc đặc trị" là sai), nhện đỏ (là sâu hại, Trichoderma không có tác dụng) và lá khỏe
  (khuyến nghị riêng, không theo cấp).
"""

PESTICIDE_NOTE = (
    'Thuốc bảo vệ thực vật dùng theo Danh mục thuốc BVTV được phép sử dụng tại Việt Nam, đúng hướng dẫn '
    'trên nhãn.'
)

_UMN_LEAF_SPOT = (
    'University of Minnesota Extension, Tomato leaf spot diseases',
    'https://extension.umn.edu/plant-diseases/tomato-leaf-spot-diseases',
)
_VAAS_2020 = (
    'Trần Ngọc Hùng, Đặng Thị Mai, Phạm Thị Xuân (2020), Tạp chí KH&CN Nông nghiệp Việt Nam, số 9(118)',
    'https://tapchi.vaas.vn/sites/tapchi.vaas.vn/files/tapchi/2021-03/Bai%2013_So%209-2020.pdf',
)

DISEASE_RECOMMENDATIONS = {
    'Tomato___Bacterial_spot': {
        'cause': 'Vi khuẩn Xanthomonas (X. euvesicatoria, X. vesicatoria, X. perforans, X. gardneri).',
        'advice': (
            'Dùng hạt giống sạch, xử lý hạt bằng nước nóng. Tưới gốc, không tưới phun lên lá; không chạm vào '
            'cây khi lá ướt; khử trùng dụng cụ. Luân canh ít nhất 1 năm, tiêu hủy tàn dư. Khi nóng ẩm, phun '
            'phòng thuốc gốc đồng; thuốc chỉ phòng, không chữa được cây đã bệnh, và vi khuẩn có thể nhờn đồng '
            'nếu phun nhiều.'
        ),
        'sources': (
            ('UW–Madison PDDC, Bacterial spot of tomato',
             'https://pddc.wisc.edu/2017/02/17/bacterial-spot-tomato/'),
            ('NC State Extension, Manage bacterial spot on your tomato transplants',
             'https://plantpathology.ces.ncsu.edu/2021/03/manage-bacterial-spot-on-your-tomato-transplants/'),
        ),
        'replaces_severity_advice': False,
    },
    'Tomato___Early_blight': {
        'cause': 'Nấm Alternaria solani.',
        'advice': (
            'Cắt bỏ lá già bị bệnh, làm giàn và phủ gốc để đất không bắn lên lá. Diệt cỏ họ cà và cây cà chua, '
            'khoai tây mọc dại. Luân canh để tàn dư kịp phân hủy. Khi bắt đầu có triệu chứng và thời tiết '
            'thuận lợi cho bệnh, phun thuốc trừ nấm theo danh mục, luân phiên nhóm hoạt chất.'
        ),
        'sources': (
            ('UC IPM, Early blight', 'https://ipm.ucanr.edu/agriculture/tomato/Early-Blight'),
            _UMN_LEAF_SPOT,
        ),
        'replaces_severity_advice': False,
    },
    'Tomato___Late_blight': {
        'cause': 'Phytophthora infestans.',
        'advice': (
            'Bệnh lan rất nhanh khi ẩm độ trên 90% và trời mát (khoảng 15–26 °C); bào tử bay theo gió. Thuốc '
            'hóa học ngày càng kém hiệu quả do mầm bệnh thay đổi độc tính, nên ưu tiên giống chống chịu (ở Việt '
            'Nam đã có giống lai mang gen kháng Ph3), cây con sạch bệnh, tránh tưới phun. Phun phòng thuốc trừ '
            'bệnh trước khi bệnh xuất hiện khi thời tiết thuận lợi, luân phiên nhóm hoạt chất. Nhổ, tiêu hủy '
            'cây bệnh và cây ký chủ mọc dại (cà chua, khoai tây).'
        ),
        'sources': (
            ('UC IPM, Late blight', 'https://ipm.ucanr.edu/agriculture/tomato/late-blight/'),
            _VAAS_2020,
        ),
        'replaces_severity_advice': False,
    },
    'Tomato___Leaf_Mold': {
        'cause': 'Nấm Passalora fulva (tên cũ Fulvia fulva).',
        'advice': (
            'Gặp chủ yếu trong nhà màng, bệnh không phát sinh khi ẩm độ dưới 85%. Bào tử lây theo mưa, gió, '
            'dụng cụ, quần áo người làm và có thể có trên hạt giống. Dùng hạt giống sạch hoặc xử lý hạt bằng '
            'nước nóng. Giảm ẩm: không làm ướt lá, dùng quạt cho thông khí, làm giàn và tỉa cành; trong nhà '
            'màng giữ nhiệt độ ban đêm cao hơn bên ngoài. Tiêu hủy tàn dư sau thu hoạch, vệ sinh kỹ nhà màng '
            'giữa các vụ. Thuốc trừ nấm theo danh mục có hiệu quả với bệnh này.'
        ),
        'sources': (
            ('UMass Extension, Tomato leaf mold',
             'https://www.umass.edu/agriculture-food-environment/vegetable/fact-sheets/tomato-leaf-mold'),
        ),
        'replaces_severity_advice': False,
    },
    'Tomato___Septoria_leaf_spot': {
        'cause': 'Nấm Septoria lycopersici.',
        'advice': (
            'Mầm bệnh trong đất bắn lên lá dưới khi tưới, mưa. Làm giàn, tỉa lá phía dưới, phủ gốc (vải phủ, '
            'rơm, màng nhựa, lá khô; không dùng cỏ, lá từ bãi cỏ đã phun thuốc diệt cỏ). Tưới gốc hoặc tưới nhỏ '
            'giọt, giữ lá khô; trồng thưa, làm cỏ cho thông thoáng. Không làm việc trên ruộng khi lá ướt. Luân '
            'canh 2 năm không trồng cà chua, ớt trên cùng chỗ; không giữ hạt giống từ cây bệnh. Ngắt bỏ lá '
            'bệnh. Vườn nhà thường không cần phun thuốc trừ nấm: cây chịu được mất nhiều lá mà không giảm số '
            'quả, nên ưu tiên các biện pháp canh tác trên.'
        ),
        'sources': (
            _UMN_LEAF_SPOT,
            ('UW–Madison Extension, Septoria leaf spot', 'https://hort.extension.wisc.edu/articles/septoria-leaf-spot/'),
        ),
        'replaces_severity_advice': False,
    },
    'Tomato___Spider_mites Two-spotted_spider_mite': {
        'cause': 'Nhện Tetranychus urticae (sâu hại, không phải bệnh).',
        'advice': (
            'Nhện tăng nhanh nhất khi nóng, khô (khoảng 20–30 °C, ẩm độ 30–50%). Kiểm tra cây hằng tuần: tìm '
            'chấm vàng trắng li ti trên lá, lật mặt dưới lá già (dùng kính lúp 10–20x) để tìm nhện, trứng và tơ. '
            'Không bón thừa đạm, không để cây thiếu nước, làm sạch cỏ dại quanh vườn; nhện bám theo quần áo nên '
            'làm việc ở khu có nhện vào cuối ngày. Có thể thả nhện bắt mồi (có bán thương mại). Khi cần, dùng '
            'thuốc trừ nhện (không phải thuốc trừ nấm) theo danh mục, phun kỹ mặt dưới lá; trứng chịu thuốc tốt '
            'hơn nên thường phải phun nhắc lại. Luân phiên nhóm hoạt chất vì nhện kháng thuốc rất nhanh.'
        ),
        'sources': (
            ('UConn IPM, Managing two-spotted mites in the greenhouse', 'https://ipm.cahnr.uconn.edu/?p=13829'),
        ),
        'replaces_severity_advice': True,
    },
    'Tomato___Target_Spot': {
        'cause': 'Nấm Corynespora cassiicola.',
        'advice': (
            'Dễ nhầm với đốm vòng và đốm vi khuẩn. Bào tử lây theo gió, mưa; bệnh phát mạnh khi nóng ẩm (khoảng '
            '28–32 °C) và lá ướt liên tục, thường bắt đầu từ bên trong tán dày, lá già dễ nhiễm hơn lá non. Chưa '
            'có giống kháng thương mại. Luân canh với cây ngoài họ cà, dùng cây con sạch bệnh, dọn cỏ dại (nhất '
            'là cây họ cà), cây mọc dại và tàn dư cây bệnh. Biện pháp chính là phun phòng thuốc trừ nấm theo danh '
            'mục đúng lúc, luân phiên nhóm hoạt chất vì nấm đã giảm nhạy với một số nhóm thuốc.'
        ),
        'sources': (
            ('UF/IFAS EDIS PP351, Target spot of tomato in Florida', 'https://edis.ifas.ufl.edu/publication/PP351'),
        ),
        'replaces_severity_advice': False,
    },
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus': {
        'cause': (
            'Virus TYLCV, do bọ phấn trắng (Bemisia tabaci) truyền. Ở đồng bằng sông Hồng, virus gây xoăn vàng '
            'lá được xác định là ToLCHnV (Tomato leaf curl Hainan virus).'
        ),
        'advice': (
            'Không có thuốc chữa, chủ yếu là phòng; ở Việt Nam bệnh hại nặng nhất vụ Thu Đông và Xuân Hè. Dùng '
            'giống kháng (mang gen Ty2, Ty3), cây con sạch bệnh; nhà màng dùng lưới chắn bọ phấn. Đặt bẫy dính '
            'vàng để theo dõi; kiểm soát bọ phấn trắng bằng thuốc trừ côn trùng theo danh mục, luân phiên. Nhổ '
            'bỏ, tiêu hủy cây bệnh; trồng xa các ruộng cà chua, ớt, đậu khác và luân canh với cây không phải ký '
            'chủ.'
        ),
        'sources': (
            ('NC State Extension, Tomato yellow leaf curl virus',
             'https://content.ces.ncsu.edu/tomato-yellow-leaf-curl-virus'),
            _VAAS_2020,
        ),
        'replaces_severity_advice': True,
    },
    'Tomato___Tomato_mosaic_virus': {
        'cause': 'Virus ToMV (gần với virus khảm thuốc lá TMV).',
        'advice': (
            'Không có thuốc chữa. Virus lây qua hạt giống và lây cơ học (dụng cụ, tay người làm, ghép cây), '
            'không do côn trùng truyền. Dùng giống kháng, hạt giống sạch; rửa tay, khử trùng dụng cụ khi tỉa '
            'cành. Nhổ bỏ, tiêu hủy cây bệnh.'
        ),
        'sources': (
            ('Ohio State University, Tomato mosaic', 'https://u.osu.edu/vegetablediseasefacts/?p=1269'),
        ),
        'replaces_severity_advice': True,
    },
    'Tomato___healthy': {
        'cause': None,
        'advice': 'Không cần xử lý. Tiếp tục chăm sóc và theo dõi định kỳ để phát hiện sớm sâu bệnh.',
        'sources': (
            ('UC IPM, Tomato pest management guidelines', 'https://ipm.ucanr.edu/agriculture/tomato/'),
        ),
        'replaces_severity_advice': True,
    },
}


def disease_recommendation(code: str) -> dict | None:
    """Khuyến nghị của một mã bệnh, dạng API trả về. None nếu mã không có trong bảng."""
    item = DISEASE_RECOMMENDATIONS.get(code)
    if item is None:
        return None
    return {
        'cause': item['cause'],
        'advice': item['advice'],
        'sources': [{'title': title, 'url': url} for title, url in item['sources']],
        'replaces_severity_advice': item['replaces_severity_advice'],
        'pesticide_note': None if item['cause'] is None else PESTICIDE_NOTE,
    }
