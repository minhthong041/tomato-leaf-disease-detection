import SpaIcon from '@mui/icons-material/Spa';
import { Box } from '@mui/material';

// Biểu tượng của ứng dụng: ô vuông bo góc màu xanh lá với hình chiếc lá
export default function BrandMark({ size = 36 }) {
  return (
    <Box aria-hidden sx={{
      width: size, height: size, flexShrink: 0, borderRadius: `${Math.round(size / 3.5)}px`,
      display: 'grid', placeItems: 'center', bgcolor: 'primary.main', color: 'common.white',
    }}>
      <SpaIcon sx={{ fontSize: size * 0.6 }} />
    </Box>
  );
}
