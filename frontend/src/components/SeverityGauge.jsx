import { Box, Stack, Typography } from '@mui/material';

import { SEVERITY_LEVELS } from '../constants/diagnosis';

// Thanh đo 5 cấp, tô đậm cấp hiện tại
export default function SeverityGauge({ level }) {
  const current = SEVERITY_LEVELS[level];

  return (
    <Box>
      <Stack direction="row" spacing={0.5} role="meter" aria-valuemin={0} aria-valuemax={4}
        aria-valuenow={level} aria-valuetext={current?.label}>
        {SEVERITY_LEVELS.map((item) => (
          <Box
            key={item.level}
            sx={{
              flex: 1,
              height: item.level === level ? 20 : 12,
              alignSelf: 'center',
              bgcolor: item.color,
              opacity: item.level === level ? 1 : 0.25,
              borderRadius: 1,
            }}
          />
        ))}
      </Stack>
      <Stack direction="row" spacing={0.5} sx={{ mt: 0.5 }}>
        {SEVERITY_LEVELS.map((item) => (
          <Typography key={item.level} variant="caption" align="center" sx={{ flex: 1 }}
            color={item.level === level ? 'text.primary' : 'text.secondary'}>
            Cấp {item.level}
          </Typography>
        ))}
      </Stack>
      {current && (
        <Typography variant="h6" sx={{ mt: 1, color: current.color }}>
          {current.label} <Typography component="span" color="text.secondary">({current.range})</Typography>
        </Typography>
      )}
    </Box>
  );
}
