import {
  Box, Chip, Slider, Stack, ToggleButton, ToggleButtonGroup, Typography,
} from '@mui/material';
import { useId, useState } from 'react';

// Kích thước ảnh sau tiền xử lý (preprocessing.TARGET_SIZE). Tọa độ bbox của từng đốm tính trên ảnh này.
const DEFAULT_SIZE = 512;

// Màu tô của từng lớp phủ: mặt nạ trắng/đen được đổi thành màu này, phần đen trong suốt
const LAYERS = [
  { key: 'leaf', step: 'leaf_mask', label: 'Mặt nạ lá', color: [47, 123, 255] },
  { key: 'lesion', step: 'lesion_mask', label: 'Mặt nạ vết bệnh', color: [255, 31, 61] },
];

const BOX_COLOR = '#ffd400';

function stepImage(steps, name) {
  return steps?.find((item) => item.step === name)?.image ?? null;
}

// Bộ lọc SVG đổi ảnh mặt nạ (0/255) thành một lớp màu: kênh alpha lấy theo độ sáng của mặt nạ.
// Không cần đọc điểm ảnh bằng canvas nên không vướng CORS khi ảnh nằm ở backend khác cổng.
function MaskFilters({ ids }) {
  return (
    <Box component="svg" aria-hidden="true" sx={{ position: 'absolute', width: 0, height: 0 }}>
      {LAYERS.map((layer) => {
        const [r, g, b] = layer.color.map((value) => value / 255);
        return (
          <filter key={layer.key} id={ids[layer.key]} colorInterpolationFilters="sRGB">
            <feColorMatrix type="matrix" values={`0 0 0 0 ${r}  0 0 0 0 ${g}  0 0 0 0 ${b}  1 0 0 0 0`} />
          </filter>
        );
      })}
    </Box>
  );
}

// Khung bao một đốm bệnh, tọa độ theo % để co giãn cùng ảnh
function LesionBox({ lesion, number, size, active, interactive, onHighlight }) {
  const [x, y, width, height] = lesion.bbox;
  return (
    <Box
      onMouseEnter={interactive ? () => onHighlight(number - 1) : undefined}
      onMouseLeave={interactive ? () => onHighlight(null) : undefined}
      sx={{
        position: 'absolute',
        left: `${(x / size) * 100}%`, top: `${(y / size) * 100}%`,
        width: `${(width / size) * 100}%`, height: `${(height / size) * 100}%`,
        minWidth: 4, minHeight: 4,
        border: active ? `2px solid ${BOX_COLOR}` : '1px solid rgba(255, 212, 0, 0.85)',
        boxShadow: active ? '0 0 0 2px rgba(0, 0, 0, 0.55)' : 'none',
        pointerEvents: interactive ? 'auto' : 'none',
        zIndex: active ? 2 : 1,
      }}
    >
      {active && (
        <Box sx={{
          position: 'absolute', bottom: '100%', left: -2, mb: '2px', px: 0.5, borderRadius: '4px',
          bgcolor: BOX_COLOR, color: '#1c2b22', fontSize: '0.7rem', fontWeight: 700, lineHeight: 1.5,
          whiteSpace: 'nowrap',
        }}>
          #{number}
        </Box>
      )}
    </Box>
  );
}

// Xem kết quả phân vùng trên ảnh đã chuẩn hóa 512×512:
// - "So sánh": kéo thanh chia để so ảnh trước xử lý với ảnh đã khoanh vết bệnh;
// - "Lớp phủ": phủ mặt nạ lá, mặt nạ vết bệnh và khung từng đốm lên ảnh.
// highlighted là chỉ số đốm đang được chọn trong bảng đốm bệnh (null nếu không có).
export default function LesionViewer({ diagnosis, highlighted, onHighlight }) {
  const baseImage = stepImage(diagnosis.steps, 'resized');
  const masks = Object.fromEntries(LAYERS.map((layer) => [layer.key, stepImage(diagnosis.steps, layer.step)]));
  const canCompare = Boolean(baseImage && diagnosis.processed_image);
  const canOverlay = Boolean(baseImage && (masks.leaf || masks.lesion));

  const [mode, setMode] = useState(canCompare ? 'compare' : 'overlay');
  const [split, setSplit] = useState(50);
  const [visible, setVisible] = useState({ leaf: false, lesion: true, boxes: true });
  const [opacity, setOpacity] = useState(55);
  const [size, setSize] = useState(DEFAULT_SIZE);

  const baseId = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const filterIds = Object.fromEntries(LAYERS.map((layer) => [layer.key, `${baseId}-${layer.key}`]));
  const lesions = diagnosis.lesions ?? [];

  // Không có ảnh bước trung gian (dữ liệu cũ): chỉ hiện ảnh kết quả
  if (!canCompare && !canOverlay) {
    return (
      <Box component="img" src={diagnosis.processed_image} alt="Ảnh đã khoanh vùng vết bệnh"
        sx={{ display: 'block', width: '100%', aspectRatio: '1 / 1', objectFit: 'cover', borderRadius: '10px' }} />
    );
  }

  const showBoxes = mode === 'overlay' ? visible.boxes : false;
  const boxes = lesions.map((lesion, index) => ({ lesion, number: index + 1 }))
    .filter(({ number }) => showBoxes || highlighted === number - 1);

  function toggleLayer(key) {
    setVisible((current) => ({ ...current, [key]: !current[key] }));
  }

  return (
    <Stack spacing={1.5}>
      <MaskFilters ids={filterIds} />

      {canCompare && canOverlay && (
        <ToggleButtonGroup size="small" exclusive value={mode} onChange={(_, value) => value && setMode(value)}
          aria-label="Cách xem ảnh" sx={{ alignSelf: 'flex-start', displayPrint: 'none' }}>
          <ToggleButton value="compare">So sánh trước / sau</ToggleButton>
          <ToggleButton value="overlay">Lớp phủ mặt nạ</ToggleButton>
        </ToggleButtonGroup>
      )}

      <Box sx={{
        position: 'relative', width: '100%', aspectRatio: '1 / 1', borderRadius: '10px', overflow: 'hidden',
        bgcolor: 'grey.900', userSelect: 'none',
      }}>
        <Box component="img" src={baseImage} alt="Ảnh lá đã chuẩn hóa 512×512" draggable={false}
          onLoad={(event) => event.currentTarget.naturalWidth && setSize(event.currentTarget.naturalWidth)}
          sx={{ position: 'absolute', inset: 0, width: '100%', height: '100%', display: 'block' }} />

        {mode === 'compare' && (
          <>
            <Box component="img" src={diagnosis.processed_image} alt="Ảnh đã khoanh vùng vết bệnh" draggable={false}
              sx={{
                position: 'absolute', inset: 0, width: '100%', height: '100%', display: 'block',
                clipPath: `inset(0 0 0 ${split}%)`,
              }} />
            <Chip size="small" label="Trước" sx={{ position: 'absolute', top: 8, left: 8, bgcolor: 'rgba(0,0,0,0.6)', color: 'common.white' }} />
            <Chip size="small" label="Sau"
              sx={{ position: 'absolute', top: 8, right: 8, bgcolor: 'rgba(0,0,0,0.6)', color: 'common.white' }} />
            {/* Ô kéo trong suốt phủ cả ảnh: kéo ở đâu cũng được, dùng được bằng phím mũi tên */}
            <Box component="input" type="range" min={0} max={100} step={1} value={split}
              onChange={(event) => setSplit(Number(event.target.value))}
              aria-label="Vị trí thanh chia ảnh trước và sau"
              sx={{
                position: 'absolute', inset: 0, width: '100%', height: '100%', m: 0, opacity: 0, zIndex: 3,
                cursor: 'ew-resize', touchAction: 'pan-y', appearance: 'none',
                '&:focus-visible + .split-handle > span': { outline: '3px solid #fff', outlineOffset: 2 },
              }} />
            <Box className="split-handle" sx={{
              position: 'absolute', top: 0, bottom: 0, left: `${split}%`, width: 2, ml: '-1px', zIndex: 2,
              bgcolor: 'common.white', boxShadow: '0 0 0 1px rgba(0,0,0,0.35)', pointerEvents: 'none',
            }}>
              <Box component="span" sx={{
                position: 'absolute', top: '50%', left: '50%', width: 32, height: 32, borderRadius: '50%',
                transform: 'translate(-50%, -50%)', bgcolor: 'common.white', boxShadow: 2,
                display: 'grid', placeItems: 'center', color: 'text.primary', fontWeight: 700, fontSize: '0.8rem',
              }}>
                ⇆
              </Box>
            </Box>
          </>
        )}

        {mode === 'overlay' && LAYERS.map((layer) => masks[layer.key] && visible[layer.key] && (
          <Box key={layer.key} component="img" src={masks[layer.key]} alt="" aria-hidden="true" draggable={false}
            sx={{
              position: 'absolute', inset: 0, width: '100%', height: '100%', display: 'block',
              filter: `url(#${filterIds[layer.key]})`, opacity: opacity / 100, pointerEvents: 'none',
            }} />
        ))}

        {boxes.map(({ lesion, number }) => (
          <LesionBox key={number} lesion={lesion} number={number} size={size}
            active={highlighted === number - 1} interactive={mode === 'overlay'} onHighlight={onHighlight} />
        ))}
      </Box>

      {mode === 'compare' ? (
        <Typography variant="body2" color="text.secondary">
          Kéo thanh chia trên ảnh để so ảnh lá đã chuẩn hóa 512×512 với ảnh đã khoanh viền đỏ quanh vết bệnh.
        </Typography>
      ) : (
        <Stack spacing={1} sx={{ displayPrint: 'none' }}>
          <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap' }}>
            {LAYERS.filter((layer) => masks[layer.key]).map((layer) => (
              <Chip key={layer.key} label={layer.label} onClick={() => toggleLayer(layer.key)}
                variant={visible[layer.key] ? 'filled' : 'outlined'} aria-pressed={visible[layer.key]}
                icon={<Box component="span" sx={{
                  width: 12, height: 12, borderRadius: '3px', ml: '6px !important',
                  bgcolor: `rgb(${layer.color.join(',')})`, opacity: visible[layer.key] ? 1 : 0.35,
                }} />} />
            ))}
            {lesions.length > 0 && (
              <Chip label={`Khung ${lesions.length} đốm bệnh`} onClick={() => toggleLayer('boxes')}
                variant={visible.boxes ? 'filled' : 'outlined'} aria-pressed={visible.boxes}
                icon={<Box component="span" sx={{
                  width: 12, height: 12, borderRadius: '2px', ml: '6px !important',
                  border: `2px solid ${BOX_COLOR}`, opacity: visible.boxes ? 1 : 0.35,
                }} />} />
            )}
          </Stack>
          <Stack direction="row" spacing={2} sx={{ alignItems: 'center', maxWidth: 360 }}>
            <Typography variant="body2" color="text.secondary" sx={{ flexShrink: 0 }}>Độ đậm lớp phủ</Typography>
            <Slider size="small" value={opacity} min={15} max={90} onChange={(_, value) => setOpacity(value)}
              aria-label="Độ đậm lớp phủ" valueLabelDisplay="auto" valueLabelFormat={(value) => `${value}%`} />
          </Stack>
        </Stack>
      )}
    </Stack>
  );
}
