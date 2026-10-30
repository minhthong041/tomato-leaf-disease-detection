import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import {
  Alert, Box, Button, Card, CardContent, CardMedia, Chip, CircularProgress, Stack, Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';

import { errorMessage } from '../api/client';
import { getDiagnosis } from '../api/diagnoses';
import BookmarkButton from '../components/BookmarkButton';
import DiseaseRecommendation from '../components/DiseaseRecommendation';
import FeedbackDialog from '../components/FeedbackDialog';
import ResultWarning from '../components/ResultWarning';
import SeverityGauge from '../components/SeverityGauge';
import StepGallery from '../components/StepGallery';
import {
  STATUS_LABELS, formatPercent, resultWarnings, showSeverityAdvice,
} from '../constants/diagnosis';

const POLL_INTERVAL_MS = 2000;
// Tiêu đề điền sẵn khi mở hộp "Báo kết quả sai" từ khung cảnh báo
const WARNING_FEEDBACK_TITLE = 'Kết quả có cảnh báo, nghi bị sai';

export default function ResultPage() {
  const { id } = useParams();
  const [diagnosis, setDiagnosis] = useState(null);
  const [error, setError] = useState('');
  const [feedbackOpen, setFeedbackOpen] = useState(false);

  // Pipeline chạy sau khi tải ảnh: hỏi lại định kỳ tới khi done/failed
  useEffect(() => {
    let timer;
    let cancelled = false;
    async function load() {
      try {
        const data = await getDiagnosis(id);
        if (cancelled) return;
        setDiagnosis(data);
        setError('');
        if (data.status === 'pending' || data.status === 'processing') {
          timer = setTimeout(load, POLL_INTERVAL_MS);
        }
      } catch (err) {
        if (!cancelled) setError(errorMessage(err));
      }
    }
    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id]);

  const backButton = (
    <Button component={Link} to="/" startIcon={<ArrowBackIcon />} sx={{ alignSelf: 'flex-start' }}>
      Chẩn đoán ảnh khác
    </Button>
  );

  if (error) {
    return <Stack spacing={2}>{backButton}<Alert severity="error">{error}</Alert></Stack>;
  }
  if (!diagnosis) {
    return <Box sx={{ display: 'grid', placeItems: 'center', py: 8 }}><CircularProgress /></Box>;
  }
  if (diagnosis.status === 'failed') {
    return (
      <Stack spacing={2}>
        {backButton}
        <Alert severity="error">{diagnosis.error_message || 'Không chẩn đoán được ảnh này.'}</Alert>
      </Stack>
    );
  }
  if (diagnosis.status !== 'done') {
    return (
      <Stack spacing={2} sx={{ py: 8, alignItems: 'center' }}>
        <CircularProgress />
        <Typography>{STATUS_LABELS[diagnosis.status]}…</Typography>
      </Stack>
    );
  }

  const { disease } = diagnosis;
  const hasWarnings = resultWarnings(diagnosis).length > 0;
  const diseaseAdvice = diagnosis.disease_recommendation;
  return (
    <Stack spacing={3}>
      <Stack direction="row" spacing={1} useFlexGap
        sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' }}>
        {backButton}
        <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap' }}>
          <BookmarkButton diagnosis={diagnosis} onChange={setDiagnosis} />
          <FeedbackDialog historyId={diagnosis.id} open={feedbackOpen} onOpenChange={setFeedbackOpen}
            suggestedTitle={hasWarnings ? WARNING_FEEDBACK_TITLE : ''} />
        </Stack>
      </Stack>

      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' } }}>
        <Card>
          <CardMedia component="img" image={diagnosis.original_image} alt="Ảnh gốc" />
          <CardContent><Typography variant="subtitle2">Ảnh gốc</Typography></CardContent>
        </Card>
        <Card>
          <CardMedia component="img" image={diagnosis.processed_image} alt="Ảnh đã khoanh vùng vết bệnh" />
          <CardContent><Typography variant="subtitle2">Vết bệnh đã khoanh vùng</Typography></CardContent>
        </Card>
      </Box>

      <ResultWarning diagnosis={diagnosis} onReport={() => setFeedbackOpen(true)} />

      <Card>
        <CardContent>
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} useFlexGap sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
              <Typography variant="h5" component="h1">
                {disease?.is_healthy ? 'Lá khỏe mạnh' : disease?.name}
              </Typography>
              <Chip size="small" label={`Độ tin cậy ${formatPercent(diagnosis.disease_confidence, 1)}`} />
            </Stack>
            <Typography>
              Tỷ lệ diện tích bệnh <strong>S = {formatPercent(diagnosis.infected_ratio)}</strong>
              {' '}· {diagnosis.lesion_count} đốm bệnh
            </Typography>
            <SeverityGauge level={diagnosis.severity_level} />
            {showSeverityAdvice(diagnosis) && (
              <Alert severity={diagnosis.severity_level >= 2 ? 'warning' : 'success'}>
                <strong>Khuyến nghị IPM theo cấp độ:</strong> {diagnosis.recommendation}
              </Alert>
            )}
          </Stack>
        </CardContent>
      </Card>

      <DiseaseRecommendation disease={disease} recommendation={diseaseAdvice} />

      {diagnosis.steps?.length > 0 && (
        <Box>
          <Typography variant="h6" gutterBottom>Các bước xử lý ảnh</Typography>
          <StepGallery steps={diagnosis.steps} />
        </Box>
      )}
    </Stack>
  );
}
