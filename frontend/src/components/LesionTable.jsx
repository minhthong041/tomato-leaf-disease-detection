import {
  Box, Button, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography,
} from '@mui/material';
import { useState } from 'react';

// Số đốm hiện sẵn; còn lại bấm "Xem thêm"
const INITIAL_ROWS = 8;

const numberFormat = new Intl.NumberFormat('vi-VN');
const decimalFormat = new Intl.NumberFormat('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// Bảng số đo từng đốm bệnh (trường lesions của kết quả), xếp theo diện tích giảm dần.
// Số thứ tự # theo thứ tự backend trả về, trùng nhãn khung trên ảnh. Rê chuột hoặc focus vào dòng
// thì khung của đốm đó sáng lên trên ảnh (onHighlight).
export default function LesionTable({ lesions, leafArea, highlighted, onHighlight }) {
  const [expanded, setExpanded] = useState(false);
  const rows = lesions.map((lesion, index) => ({ ...lesion, index })).sort((a, b) => b.area - a.area);

  return (
    <Box>
      <TableContainer sx={{ border: 1, borderColor: 'divider', borderRadius: '10px' }}>
        <Table size="small" aria-label="Số đo từng đốm bệnh">
          <TableHead>
            <TableRow sx={{ '& th': { fontWeight: 600, color: 'text.secondary', whiteSpace: 'nowrap', bgcolor: 'background.default' } }}>
              <TableCell>#</TableCell>
              <TableCell align="right">Diện tích (px)</TableCell>
              <TableCell align="right">% diện tích lá</TableCell>
              <TableCell align="right">Chu vi (px)</TableCell>
              <TableCell align="right">Độ tròn</TableCell>
              <TableCell align="right">Tâm (x, y)</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {/* Dòng sau INITIAL_ROWS chỉ ẩn trên màn hình: bản in luôn có đủ các đốm */}
            {rows.map((row, position) => (
              <TableRow key={row.index} hover tabIndex={0} selected={highlighted === row.index}
                onMouseEnter={() => onHighlight(row.index)} onMouseLeave={() => onHighlight(null)}
                onFocus={() => onHighlight(row.index)} onBlur={() => onHighlight(null)}
                sx={{
                  cursor: 'default', '& td': { fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' },
                  ...(!expanded && position >= INITIAL_ROWS && { display: 'none', displayPrint: 'table-row' }),
                }}>
                <TableCell sx={{ fontWeight: 600 }}>{row.index + 1}</TableCell>
                <TableCell align="right">{numberFormat.format(row.area)}</TableCell>
                <TableCell align="right">
                  {leafArea ? `${decimalFormat.format((row.area / leafArea) * 100)}%` : '—'}
                </TableCell>
                <TableCell align="right">{decimalFormat.format(row.perimeter)}</TableCell>
                <TableCell align="right">{decimalFormat.format(row.circularity)}</TableCell>
                <TableCell align="right">({row.center[0]}, {row.center[1]})</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      {rows.length > INITIAL_ROWS && (
        <Button size="small" onClick={() => setExpanded((value) => !value)} sx={{ mt: 1, displayPrint: 'none' }}>
          {expanded ? 'Thu gọn' : `Xem thêm ${rows.length - INITIAL_ROWS} đốm`}
        </Button>
      )}
      <Typography variant="caption" color="text.secondary" component="p" sx={{ mt: 1 }}>
        Đo trên ảnh 512×512. Độ tròn = 4π·diện tích / chu vi², bằng 1 với hình tròn; ảnh không vuông bị kéo giãn
        khi chuẩn hóa nên độ tròn chỉ để tham khảo.
      </Typography>
    </Box>
  );
}
