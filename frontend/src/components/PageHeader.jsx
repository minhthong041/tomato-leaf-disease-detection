import { Box, Stack, Typography } from '@mui/material';

// Tiêu đề đầu mỗi trang: dòng nhỏ phía trên (overline), tiêu đề, mô tả và nút bên phải (actions)
export default function PageHeader({ overline, title, description, actions }) {
  return (
    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} useFlexGap
      sx={{ justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'flex-end' } }}>
      <Box sx={{ minWidth: 0 }}>
        {overline && <Typography variant="overline" color="primary">{overline}</Typography>}
        <Typography variant="h4" component="h1" sx={{ fontSize: { xs: '1.6rem', sm: '2.125rem' } }}>
          {title}
        </Typography>
        {description && (
          <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 720 }}>{description}</Typography>
        )}
      </Box>
      {actions}
    </Stack>
  );
}
