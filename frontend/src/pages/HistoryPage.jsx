import BookmarkIcon from '@mui/icons-material/Bookmark';
import {
  Alert, Box, Chip, CircularProgress, List, ListItemButton, ListItemIcon, ListItemText, Pagination, Stack,
  ToggleButton, ToggleButtonGroup, Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router';

import { errorMessage } from '../api/client';
import { listDiagnoses } from '../api/diagnoses';
import { SEVERITY_LEVELS, STATUS_LABELS, formatPercent } from '../constants/diagnosis';

const PAGE_SIZE = 20; // trùng PAGE_SIZE của DRF
const FILTER_PARAM = 'filter'; // ?filter=saved giữ bộ lọc khi quay lại từ trang kết quả
const FILTER_ALL = 'all';
const FILTER_SAVED = 'saved';

export default function HistoryPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const filter = searchParams.get(FILTER_PARAM) === FILTER_SAVED ? FILTER_SAVED : FILTER_ALL;
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    listDiagnoses(page, { bookmarkedOnly: filter === FILTER_SAVED })
      .then((result) => !cancelled && setData(result))
      .catch((err) => !cancelled && setError(errorMessage(err)));
    return () => {
      cancelled = true;
    };
  }, [page, filter]);

  // Đổi bộ lọc hoặc trang: xóa dữ liệu cũ để hiện vòng tải thay vì danh sách cũ
  function resetList() {
    setData(null);
    setError('');
  }

  function handleFilterChange(_, value) {
    if (!value || value === filter) return; // bấm lại nút đang chọn: giữ nguyên
    resetList();
    setPage(1);
    setSearchParams(value === FILTER_SAVED ? { [FILTER_PARAM]: FILTER_SAVED } : {});
  }

  const emptyText = filter === FILTER_SAVED
    ? 'Chưa lưu kết quả nào. Bấm "Lưu kết quả" trên trang kết quả để lưu lại.'
    : 'Chưa có lần chẩn đoán nào.';

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={2} useFlexGap
        sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' }}>
        <Typography variant="h4" component="h1">Lịch sử chẩn đoán</Typography>
        <ToggleButtonGroup size="small" exclusive value={filter} onChange={handleFilterChange}
          aria-label="Lọc lịch sử">
          <ToggleButton value={FILTER_ALL}>Tất cả</ToggleButton>
          <ToggleButton value={FILTER_SAVED}>
            <BookmarkIcon fontSize="small" sx={{ mr: 0.5 }} />
            Đã lưu
          </ToggleButton>
        </ToggleButtonGroup>
      </Stack>
      {error && <Alert severity="error">{error}</Alert>}
      {!data && !error && <Box sx={{ display: 'grid', placeItems: 'center', py: 8 }}><CircularProgress /></Box>}
      {data && data.results.length === 0 && <Typography color="text.secondary">{emptyText}</Typography>}
      {data && data.results.length > 0 && (
        <>
          <List>
            {data.results.map((item) => {
              const level = SEVERITY_LEVELS[item.severity_level];
              return (
                <ListItemButton key={item.id} component={Link} to={`/results/${item.id}`} divider>
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {item.is_bookmarked && <BookmarkIcon color="primary" titleAccess="Đã lưu" />}
                  </ListItemIcon>
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
              onChange={(_, value) => { if (value !== page) { resetList(); setPage(value); } }} sx={{ alignSelf: 'center' }} />
          )}
        </>
      )}
    </Stack>
  );
}
