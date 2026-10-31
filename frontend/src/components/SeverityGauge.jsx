import { Box, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';

import { SEVERITY_LEVELS } from '../constants/diagnosis';

// Thanh đo 5 cấp: mỗi cấp một ô kèm khoảng S, tô đậm cấp hiện tại
export default function SeverityGauge({ level }) {
  const current = SEVERITY_LEVELS[level];

  return (
    <Box>
      <Box role="meter" aria-label="Cấp độ bệnh" aria-valuemin={0} aria-valuemax={4}
        aria-valuenow={level} aria-valuetext={current?.label}
        sx={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 0.75 }}>
        {SEVERITY_LEVELS.map((item) => {
          const active = item.level === level;
          return (
            <Box key={item.level} sx={{ minWidth: 0 }}>
              <Box sx={{
                height: active ? 14 : 8, mt: active ? 0 : '3px', borderRadius: '4px',
                bgcolor: active ? item.color : alpha(item.color, 0.25),
                boxShadow: active ? `0 0 0 3px ${alpha(item.color, 0.2)}` : 'none',
              }} />
              <Typography variant="caption" component="div" align="center"
                sx={{ mt: 0.75, fontWeight: active ? 700 : 500, color: active ? item.color : 'text.secondary' }}>
                Cấp {item.level}
              </Typography>
              <Typography variant="caption" component="div" align="center" color="text.secondary"
                sx={{ display: { xs: 'none', sm: 'block' }, fontSize: '0.68rem', lineHeight: 1.3 }}>
                {item.range}
              </Typography>
            </Box>
          );
        })}
      </Box>
      {current && (
        <Stack direction="row" spacing={1} useFlexGap
          sx={{ mt: 1.5, alignItems: 'baseline', flexWrap: 'wrap' }}>
          <Typography variant="h6" component="p" sx={{ color: current.color, fontWeight: 700 }}>
            {current.label}
          </Typography>
          <Typography variant="body2" color="text.secondary">({current.range})</Typography>
        </Stack>
      )}
    </Box>
  );
}
