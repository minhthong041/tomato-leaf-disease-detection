import CloseIcon from '@mui/icons-material/Close';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import {
  Box, ButtonBase, Dialog, DialogContent, DialogTitle, IconButton, Stack, Typography,
} from '@mui/material';
import { useState } from 'react';

import { STEP_LABELS, STEP_STAGES } from '../constants/diagnosis';

// Ảnh trung gian của từng bước pipeline, đánh số theo thứ tự backend trả về và chia nhóm theo giai đoạn.
// Bấm vào ảnh để xem lớn.
export default function StepGallery({ steps }) {
  const [opened, setOpened] = useState(null);
  const numbered = steps.map((item, index) => ({
    ...item, number: index + 1, label: STEP_LABELS[item.step] ?? item.step,
  }));
  const grouped = new Set(STEP_STAGES.flatMap((stage) => stage.steps));
  const groups = [
    ...STEP_STAGES.map((stage) => ({
      title: stage.title, items: numbered.filter((item) => stage.steps.includes(item.step)),
    })),
    { title: 'Bước khác', items: numbered.filter((item) => !grouped.has(item.step)) },
  ].filter((group) => group.items.length > 0);

  return (
    <>
      <Stack spacing={3}>
        {groups.map((group) => (
          <Box key={group.title}>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1.25 }}>{group.title}</Typography>
            <Box sx={{
              display: 'grid', gap: { xs: 1.25, sm: 2 },
              gridTemplateColumns: { xs: 'repeat(2, 1fr)', sm: 'repeat(3, 1fr)', md: 'repeat(4, 1fr)' },
            }}>
              {group.items.map((item) => (
                <ButtonBase key={item.step} onClick={() => setOpened(item)} focusRipple
                  aria-label={`Xem lớn: ${item.number}. ${item.label}`}
                  sx={{
                    display: 'block', textAlign: 'left', borderRadius: '10px', overflow: 'hidden',
                    border: 1, borderColor: 'divider', bgcolor: 'background.paper',
                    '&:hover .zoom-hint': { opacity: 1 },
                  }}>
                  <Box sx={{ position: 'relative', bgcolor: 'grey.900' }}>
                    <Box component="img" src={item.image} alt={item.label} loading="lazy"
                      sx={{ display: 'block', width: '100%', aspectRatio: '1 / 1', objectFit: 'cover' }} />
                    <Box className="zoom-hint" sx={{
                      position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', opacity: 0,
                      bgcolor: 'rgba(0, 0, 0, 0.35)', color: 'common.white', transition: 'opacity 0.15s',
                    }}>
                      <ZoomInIcon fontSize="large" />
                    </Box>
                  </Box>
                  <Stack direction="row" spacing={1} sx={{ p: 1.25, alignItems: 'flex-start' }}>
                    <Box sx={{
                      minWidth: 22, height: 22, borderRadius: '50%', display: 'grid', placeItems: 'center',
                      bgcolor: 'primary.light', color: 'primary.main', fontSize: '0.75rem', fontWeight: 700,
                    }}>
                      {item.number}
                    </Box>
                    <Typography variant="body2" sx={{ fontWeight: 500, lineHeight: 1.35 }}>{item.label}</Typography>
                  </Stack>
                </ButtonBase>
              ))}
            </Box>
          </Box>
        ))}
      </Stack>

      <Dialog open={Boolean(opened)} onClose={() => setOpened(null)} maxWidth="sm" fullWidth>
        {opened && (
          <>
            <DialogTitle sx={{ pr: 6 }}>
              {opened.number}. {opened.label}
              <IconButton onClick={() => setOpened(null)} aria-label="Đóng"
                sx={{ position: 'absolute', right: 8, top: 8 }}>
                <CloseIcon />
              </IconButton>
            </DialogTitle>
            <DialogContent>
              <Box component="img" src={opened.image} alt={opened.label}
                sx={{ display: 'block', width: '100%', borderRadius: '8px', bgcolor: 'grey.900' }} />
            </DialogContent>
          </>
        )}
      </Dialog>
    </>
  );
}
