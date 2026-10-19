import {
  Alert, Box, Chip, CircularProgress, List, ListItemButton, ListItemText, Pagination, Stack, Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';
import { Link } from 'react-router';

import { errorMessage } from '../api/client';
import { listDiagnoses } from '../api/diagnoses';
import { SEVERITY_LEVELS, STATUS_LABELS, formatPercent } from '../constants/diagnosis';

const PAGE_SIZE = 20; // trùng PAGE_SIZE của DRF

export default function HistoryPage() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    listDiagnoses(page)
      .then((result) => !cancelled && setData(result))
      .catch((err) => !cancelled && setError(errorMessage(err)));
    return () => {
      cancelled = true;
    };
  }, [page]);

  return (
    <Stack spacing={2}>
      <Typography variant="h4" component="h1">Lịch sử chẩn đoán</Typography>
      {error && <Alert severity="error">{error}</Alert>}
      {!data && !error && <Box sx={{ display: 'grid', placeItems: 'center', py: 8 }}><CircularProgress /></Box>}
      {data && data.results.length === 0 && <Typography color="text.secondary">Chưa có lần chẩn đoán nào.</Typography>}
      {data && data.results.length > 0 && (
        <>
          <List>
            {data.results.map((item) => {
              const level = SEVERITY_LEVELS[item.severity_level];
              return (
                <ListItemButton key={item.id} component={Link} to={`/results/${item.id}`} divider>
                  <ListItemText
                    primary={item.status === 'done' ? (item.disease?.name ?? '—') : STATUS_LABELS[item.status]}
                    secondary={new Date(item.created_at).toLocaleString('vi-VN')}
                  />
                  {level && (
                    <Chip label={`${level.label} · ${formatPercent(item.infected_ratio)}`}
                      sx={{ bgcolor: level.color, color: 'common.white' }} />
                  )}
                </ListItemButton>
              );
            })}
          </List>
          {data.count > PAGE_SIZE && (
            <Pagination count={Math.ceil(data.count / PAGE_SIZE)} page={page}
              onChange={(_, value) => setPage(value)} sx={{ alignSelf: 'center' }} />
          )}
        </>
      )}
    </Stack>
  );
}
