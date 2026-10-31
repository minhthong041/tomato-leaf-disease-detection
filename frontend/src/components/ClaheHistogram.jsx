import { Alert, Box, CircularProgress, Stack, Typography } from '@mui/material';
import { useEffect, useRef, useState } from 'react';

// Histogram kênh L* (CIELAB, 0–100) của ảnh trước CLAHE (bước denoised) và sau CLAHE (bước clahe).
// Tính ngay trên trình duyệt từ ảnh PNG của hai bước, không cần API riêng.

const BIN_WIDTH = 2; // mỗi cột rộng 2 đơn vị L*
const BIN_COUNT = 100 / BIN_WIDTH;
const HEIGHT = 236;
const MARGIN = { top: 12, right: 16, bottom: 46, left: 44 };
// Hai màu đã kiểm tra tách biệt cho người mù màu (dataviz validate_palette: ΔE ≥ 19)
const SERIES = [
  { key: 'before', label: 'Trước CLAHE (sau khử nhiễu)', color: '#7a5cc7', dash: '5 4' },
  { key: 'after', label: 'Sau CLAHE', color: '#1f6f43', dash: null },
];

const percentFormat = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1, minimumFractionDigits: 1 });
const statFormat = new Intl.NumberFormat('vi-VN', { maximumFractionDigits: 1, minimumFractionDigits: 1 });

// sRGB 0–255 -> độ sáng tuyến tính, tra bảng cho nhanh
const LINEAR = Array.from({ length: 256 }, (_, value) => {
  const c = value / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
});

function lightness(r, g, b) {
  const y = 0.2126729 * LINEAR[r] + 0.7151522 * LINEAR[g] + 0.072175 * LINEAR[b];
  const f = y > 0.008856 ? Math.cbrt(y) : 7.787 * y + 16 / 116;
  return 116 * f - 16;
}

async function lightnessHistogram(url) {
  const response = await fetch(url, { mode: 'cors' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const bitmap = await createImageBitmap(await response.blob());
  const canvas = document.createElement('canvas');
  canvas.width = bitmap.width;
  canvas.height = bitmap.height;
  const context = canvas.getContext('2d', { willReadFrequently: true });
  context.drawImage(bitmap, 0, 0);
  const { data } = context.getImageData(0, 0, bitmap.width, bitmap.height);

  const counts = new Array(BIN_COUNT).fill(0);
  let sum = 0;
  let sumSquares = 0;
  const total = data.length / 4;
  for (let i = 0; i < data.length; i += 4) {
    const l = lightness(data[i], data[i + 1], data[i + 2]);
    counts[Math.min(BIN_COUNT - 1, Math.max(0, Math.floor(l / BIN_WIDTH)))] += 1;
    sum += l;
    sumSquares += l * l;
  }
  const mean = sum / total;
  return {
    bins: counts.map((count) => (count / total) * 100),
    mean,
    std: Math.sqrt(Math.max(0, sumSquares / total - mean * mean)),
  };
}

// Bước chia trục tung đẹp (1, 2, 2.5, 5 × 10^n), khoảng 4 vạch
function niceStep(max) {
  const raw = max / 4;
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].find((value) => value * magnitude >= raw) * magnitude;
  return step;
}

function Chart({ data, width }) {
  const [hover, setHover] = useState(null);
  const plotWidth = width - MARGIN.left - MARGIN.right;
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom;
  const maxValue = Math.max(...SERIES.flatMap((series) => data[series.key].bins));
  const step = niceStep(maxValue);
  const yMax = Math.ceil(maxValue / step) * step;
  const yTicks = Array.from({ length: Math.round(yMax / step) + 1 }, (_, index) => index * step);
  const x = (l) => MARGIN.left + (l / 100) * plotWidth;
  const y = (value) => MARGIN.top + plotHeight - (value / yMax) * plotHeight;
  const binCenter = (index) => (index + 0.5) * BIN_WIDTH;

  function path(bins) {
    return bins.map((value, index) => `${index ? 'L' : 'M'}${x(binCenter(index)).toFixed(1)},${y(value).toFixed(1)}`).join('');
  }

  function handlePointerMove(event) {
    const box = event.currentTarget.getBoundingClientRect();
    const l = ((event.clientX - box.left - MARGIN.left) / plotWidth) * 100;
    setHover(l < 0 || l > 100 ? null : Math.min(BIN_COUNT - 1, Math.floor(l / BIN_WIDTH)));
  }

  const tooltipLeft = hover == null ? 0 : x(binCenter(hover));
  return (
    <Box sx={{ position: 'relative' }}>
      <svg width={width} height={HEIGHT} role="img" style={{ display: 'block', touchAction: 'pan-y' }}
        aria-label={`Histogram độ sáng L*: trung bình ${statFormat.format(data.before.mean)} trước CLAHE và `
          + `${statFormat.format(data.after.mean)} sau CLAHE`}
        onPointerMove={handlePointerMove} onPointerLeave={() => setHover(null)}>
        {yTicks.map((tick) => (
          <g key={tick}>
            <line x1={MARGIN.left} x2={width - MARGIN.right} y1={y(tick)} y2={y(tick)}
              stroke="#e3e7df" strokeWidth={1} />
            <text x={MARGIN.left - 8} y={y(tick)} dy="0.32em" textAnchor="end" fontSize={11} fill="#5c6b61">
              {percentFormat.format(tick)}%
            </text>
          </g>
        ))}
        {[0, 25, 50, 75, 100].map((tick) => (
          <text key={tick} x={x(tick)} y={HEIGHT - 26} textAnchor="middle" fontSize={11} fill="#5c6b61">{tick}</text>
        ))}
        <text x={MARGIN.left + plotWidth / 2} y={HEIGHT - 6} textAnchor="middle" fontSize={11} fill="#5c6b61">
          Độ sáng L* (0 = đen, 100 = trắng)
        </text>
        {hover != null && (
          <line x1={tooltipLeft} x2={tooltipLeft} y1={MARGIN.top} y2={MARGIN.top + plotHeight}
            stroke="#1c2b22" strokeOpacity={0.35} strokeWidth={1} />
        )}
        {SERIES.map((series) => (
          <path key={series.key} d={path(data[series.key].bins)} fill="none" stroke={series.color}
            strokeWidth={2} strokeDasharray={series.dash ?? undefined} strokeLinejoin="round" strokeLinecap="round" />
        ))}
        {hover != null && SERIES.map((series) => (
          <circle key={series.key} cx={tooltipLeft} cy={y(data[series.key].bins[hover])} r={4}
            fill={series.color} stroke="#fff" strokeWidth={2} />
        ))}
      </svg>
      {hover != null && (
        <Box sx={{
          position: 'absolute', top: 4, pointerEvents: 'none', px: 1.25, py: 0.75, borderRadius: '8px',
          bgcolor: 'background.paper', border: 1, borderColor: 'divider', boxShadow: 2, fontSize: '0.8rem',
          ...(tooltipLeft > width / 2 ? { right: width - tooltipLeft + 10 } : { left: tooltipLeft + 10 }),
        }}>
          <Typography variant="caption" color="text.secondary" component="p">
            L* {hover * BIN_WIDTH}–{(hover + 1) * BIN_WIDTH}
          </Typography>
          {SERIES.map((series) => (
            <Stack key={series.key} direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
              <Box sx={{ width: 10, height: 2, bgcolor: series.color }} />
              <Typography variant="caption" sx={{ whiteSpace: 'nowrap' }}>
                {series.key === 'before' ? 'Trước' : 'Sau'}: <strong>{percentFormat.format(data[series.key].bins[hover])}%</strong> điểm ảnh
              </Typography>
            </Stack>
          ))}
        </Box>
      )}
    </Box>
  );
}

export default function ClaheHistogram({ beforeUrl, afterUrl }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [width, setWidth] = useState(0);
  const containerRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([lightnessHistogram(beforeUrl), lightnessHistogram(afterUrl)])
      .then(([before, after]) => !cancelled && setData({ before, after }))
      .catch(() => !cancelled && setError(true));
    return () => {
      cancelled = true;
    };
  }, [beforeUrl, afterUrl]);

  // Vẽ theo bề rộng thật của khung để chữ trên trục không bị co giãn
  useEffect(() => {
    const element = containerRef.current;
    if (!element) return undefined;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  if (error) {
    return <Alert severity="info">Không đọc được ảnh của hai bước để vẽ histogram.</Alert>;
  }

  return (
    <Stack spacing={1.5}>
      <Stack direction="row" spacing={2.5} useFlexGap sx={{ flexWrap: 'wrap' }}>
        {SERIES.map((series) => (
          <Stack key={series.key} direction="row" spacing={1} sx={{ alignItems: 'center' }}>
            <svg width={22} height={8} aria-hidden="true">
              <line x1={1} x2={21} y1={4} y2={4} stroke={series.color} strokeWidth={2}
                strokeDasharray={series.dash ?? undefined} strokeLinecap="round" />
            </svg>
            <Typography variant="body2">
              {series.label}
              {data && (
                <Typography component="span" variant="body2" color="text.secondary">
                  {' · '}trung bình {statFormat.format(data[series.key].mean)}, độ lệch chuẩn {statFormat.format(data[series.key].std)}
                </Typography>
              )}
            </Typography>
          </Stack>
        ))}
      </Stack>
      <Box ref={containerRef} sx={{ width: '100%', minHeight: HEIGHT }}>
        {data && width > 0 ? <Chart data={data} width={width} /> : (
          <Box sx={{ height: HEIGHT, display: 'grid', placeItems: 'center' }}><CircularProgress size={28} /></Box>
        )}
      </Box>
      {data && (
        <Typography variant="body2" color="text.secondary">
          CLAHE cân bằng độ sáng riêng trên từng ô của lưới 8×8: độ lệch chuẩn của L* đổi từ {statFormat.format(data.before.std)} thành{' '}
          {statFormat.format(data.after.std)}, nghĩa là độ tương phản {data.after.std >= data.before.std ? 'tăng' : 'giảm'}.
          Chỉ kênh L đổi, hai kênh màu a*, b* giữ nguyên nên màu vết bệnh không lệch.
        </Typography>
      )}
      {data && (
        <Box component="details" sx={{ displayPrint: 'none', '& summary': { cursor: 'pointer', color: 'primary.main', fontWeight: 600, fontSize: '0.875rem' } }}>
          <summary>Xem bảng số liệu</summary>
          <Box sx={{ mt: 1, maxHeight: 240, overflow: 'auto', border: 1, borderColor: 'divider', borderRadius: '8px' }}>
            <Box component="table" sx={{
              width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', fontVariantNumeric: 'tabular-nums',
              '& th, & td': { px: 1.5, py: 0.5, textAlign: 'right', borderBottom: 1, borderColor: 'divider' },
              '& th': { position: 'sticky', top: 0, bgcolor: 'background.default', fontWeight: 600 },
            }}>
              <thead>
                <tr><th>L*</th><th>Trước CLAHE</th><th>Sau CLAHE</th></tr>
              </thead>
              <tbody>
                {data.before.bins.map((value, index) => (
                  <tr key={index}>
                    <td>{index * BIN_WIDTH}–{(index + 1) * BIN_WIDTH}</td>
                    <td>{percentFormat.format(value)}%</td>
                    <td>{percentFormat.format(data.after.bins[index])}%</td>
                  </tr>
                ))}
              </tbody>
            </Box>
          </Box>
        </Box>
      )}
    </Stack>
  );
}
