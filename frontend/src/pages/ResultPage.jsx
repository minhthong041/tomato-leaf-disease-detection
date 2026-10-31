import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutlineOutlined';
import HealthAndSafetyOutlinedIcon from '@mui/icons-material/HealthAndSafetyOutlined';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import PrintOutlinedIcon from '@mui/icons-material/PrintOutlined';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Divider, LinearProgress, Link as MuiLink, Stack,
  Typography,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router';

import { errorMessage } from '../api/client';
import { getDiagnosis } from '../api/diagnoses';
import BookmarkButton from '../components/BookmarkButton';
import ClaheHistogram from '../components/ClaheHistogram';
import DiseaseRecommendation from '../components/DiseaseRecommendation';
import FeedbackDialog from '../components/FeedbackDialog';
import LesionTable from '../components/LesionTable';
import LesionViewer from '../components/LesionViewer';
import ResultWarning from '../components/ResultWarning';
import SeverityGauge from '../components/SeverityGauge';
import StepGallery from '../components/StepGallery';
import {
  SEVERITY_LEVELS, STATUS_LABELS, formatPercent, isLowConfidence, resultWarnings, showSeverityAdvice,
} from '../constants/diagnosis';

const POLL_INTERVAL_MS = 2000;
// Tiêu đề điền sẵn khi mở hộp "Báo kết quả sai" từ khung cảnh báo
const WARNING_FEEDBACK_TITLE = 'Kết quả có cảnh báo, nghi bị sai';

// Padding chung của các card trên trang
const CARD_CONTENT_SX = { p: { xs: 2.5, sm: 3 }, '&:last-child': { pb: { xs: 2.5, sm: 3 } } };

// Một ô số liệu trong card tóm tắt
function StatTile({ label, value, color }) {
  return (
    <Box sx={{ p: 1.5, borderRadius: '10px', bgcolor: 'background.default', minWidth: 0 }}>
      <Typography variant="caption" color="text.secondary" component="p" sx={{ lineHeight: 1.3 }}>
        {label}
      </Typography>
      <Typography sx={{ fontWeight: 700, fontSize: { xs: '1.15rem', sm: '1.35rem' }, color, mt: 0.25 }} noWrap>
        {value}
      </Typography>
    </Box>
  );
}

export default function ResultPage() {
  const { id } = useParams();
  const [diagnosis, setDiagnosis] = useState(null);
  const [error, setError] = useState('');
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  // Đốm bệnh đang chọn ở bảng đốm: khung của nó sáng lên trên ảnh
  const [highlighted, setHighlighted] = useState(null);

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
    <Button component={Link} to="/" startIcon={<ArrowBackIcon />} sx={{ alignSelf: 'flex-start', ml: -1 }}>
      Chẩn đoán ảnh khác
    </Button>
  );

  if (error) {
    return <Stack spacing={2}>{backButton}<Alert severity="error">{error}</Alert></Stack>;
  }
  if (!diagnosis) {
    return <Box sx={{ display: 'grid', placeItems: 'center', py: 10 }}><CircularProgress /></Box>;
  }
  if (diagnosis.status === 'failed') {
    return (
      <Stack spacing={2} useFlexGap>
        {backButton}
        <Card sx={{ maxWidth: 640, mx: 'auto', width: '100%' }}>
          <CardContent sx={{ ...CARD_CONTENT_SX, textAlign: 'center' }}>
            <ErrorOutlineIcon color="error" sx={{ fontSize: 56 }} />
            <Typography variant="h5" component="h1" sx={{ mt: 1 }}>Không chẩn đoán được ảnh này</Typography>
            <Alert severity="error" sx={{ mt: 2, textAlign: 'left' }}>
              {diagnosis.error_message || 'Không chẩn đoán được ảnh này.'}
            </Alert>
            <Typography color="text.secondary" sx={{ mt: 2 }}>
              Hãy chụp lại <strong>một chiếc lá cà chua</strong> trên <strong>nền đơn sắc</strong>, đủ sáng và rõ nét.
            </Typography>
            <Button component={Link} to="/" variant="contained" size="large" sx={{ mt: 3 }}>
              Chọn ảnh khác
            </Button>
          </CardContent>
        </Card>
      </Stack>
    );
  }
  if (diagnosis.status !== 'done') {
    return (
      <Card sx={{ maxWidth: 480, mx: 'auto', mt: 4 }}>
        <CardContent sx={{ ...CARD_CONTENT_SX, textAlign: 'center' }}>
          <CircularProgress />
          <Typography variant="h6" component="p" sx={{ mt: 2 }}>{STATUS_LABELS[diagnosis.status]}…</Typography>
          <Typography color="text.secondary">
            Hệ thống đang tách lá, tìm vết bệnh và nhận diện tên bệnh. Thường chỉ mất vài giây.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  const { disease } = diagnosis;
  const hasWarnings = resultWarnings(diagnosis).length > 0;
  const diseaseAdvice = diagnosis.disease_recommendation;
  const level = SEVERITY_LEVELS[diagnosis.severity_level];
  const confidence = diagnosis.disease_confidence == null ? null : Number(diagnosis.disease_confidence);
  const lowConfidence = isLowConfidence(diagnosis);
  const withSeverityAdvice = showSeverityAdvice(diagnosis);
  const hasDiseaseAdvice = Boolean(disease && diseaseAdvice);
  const lesions = diagnosis.lesions ?? [];
  const stepImage = (name) => diagnosis.steps?.find((item) => item.step === name)?.image;
  const histogramImages = [stepImage('denoised'), stepImage('clahe')];

  const summary = (
    <Card>
      <CardContent sx={CARD_CONTENT_SX}>
        <Stack spacing={2.5}>
          <Box>
            <Stack direction="row" spacing={1} useFlexGap sx={{ alignItems: 'center', flexWrap: 'wrap', mb: 0.5 }}>
              <Typography variant="overline" color="text.secondary">Kết quả chẩn đoán</Typography>
              {disease && (
                <Chip size="small" variant="outlined"
                  icon={disease.is_healthy ? <CheckCircleIcon /> : <WarningAmberIcon />}
                  label={disease.is_healthy ? 'Không phát hiện bệnh' : 'Phát hiện bệnh'}
                  color={disease.is_healthy ? 'success' : 'error'} />
              )}
            </Stack>
            <Typography variant="h4" component="h1" sx={{ fontSize: { xs: '1.6rem', sm: '2rem' } }}>
              {disease?.is_healthy ? 'Lá khỏe mạnh' : disease?.name}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {new Date(diagnosis.created_at).toLocaleString('vi-VN')}
            </Typography>
          </Box>

          <Box>
            <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'baseline', mb: 0.75 }}>
              <Typography variant="body2" color="text.secondary">Độ tin cậy</Typography>
              <Typography sx={{ fontWeight: 700, color: lowConfidence ? 'warning.dark' : 'text.primary' }}>
                {formatPercent(diagnosis.disease_confidence, 1)}
              </Typography>
            </Stack>
            <LinearProgress variant="determinate" value={confidence == null ? 0 : confidence * 100}
              color={lowConfidence ? 'warning' : 'primary'}
              aria-label={`Độ tin cậy ${formatPercent(diagnosis.disease_confidence, 1)}`} />
          </Box>

          <Box sx={{ display: 'grid', gap: 1, gridTemplateColumns: 'repeat(3, 1fr)' }}>
            <StatTile label="Tỷ lệ diện tích bệnh S" value={formatPercent(diagnosis.infected_ratio)} />
            <StatTile label="Số đốm bệnh" value={diagnosis.lesion_count} />
            <StatTile label="Cấp độ" value={`Cấp ${diagnosis.severity_level}`} color={level?.color} />
          </Box>

          <Divider />

          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1.5 }}>Mức độ nghiêm trọng (theo tỷ lệ S)</Typography>
            <SeverityGauge level={diagnosis.severity_level} />
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );

  return (
    <Stack spacing={3}>
      {/* Chỉ hiện khi in: trang in không có thanh điều hướng nên ghi tên hệ thống và mã kết quả */}
      <Typography variant="body2" color="text.secondary" sx={{ display: 'none', displayPrint: 'block' }}>
        Chẩn Đoán Bệnh Lá Cà Chua · Kết quả #{diagnosis.id}
      </Typography>

      <Stack direction="row" spacing={1} useFlexGap
        sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', displayPrint: 'none' }}>
        {backButton}
        <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: 'wrap' }}>
          <Button variant="outlined" startIcon={<PrintOutlinedIcon />} onClick={() => window.print()}>
            In / Lưu PDF
          </Button>
          <BookmarkButton diagnosis={diagnosis} onChange={setDiagnosis} />
          <FeedbackDialog historyId={diagnosis.id} open={feedbackOpen} onOpenChange={setFeedbackOpen}
            suggestedTitle={hasWarnings ? WARNING_FEEDBACK_TITLE : ''} />
        </Stack>
      </Stack>

      <ResultWarning diagnosis={diagnosis} onReport={() => setFeedbackOpen(true)} />

      <Box sx={{ display: 'grid', gap: 3, gridTemplateColumns: { xs: '1fr', md: '7fr 5fr' }, alignItems: 'start' }}>
        {/* Điện thoại: card tóm tắt lên trước ảnh */}
        <Box sx={{ order: { xs: 2, md: 1 }, minWidth: 0 }}>
          <Card>
            <CardContent sx={CARD_CONTENT_SX}>
              <Stack direction="row" spacing={1} useFlexGap
                sx={{ justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', mb: 2 }}>
                <Typography variant="h6" component="h2">Ảnh phân tích</Typography>
                <MuiLink href={diagnosis.original_image} target="_blank" rel="noopener" variant="body2"
                  sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, displayPrint: 'none' }}>
                  Mở ảnh gốc đã tải lên <OpenInNewIcon sx={{ fontSize: 16 }} />
                </MuiLink>
              </Stack>
              <LesionViewer diagnosis={diagnosis} highlighted={highlighted} onHighlight={setHighlighted} />
              {lesions.length > 0 && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="subtitle1" component="h3">Chi tiết từng đốm bệnh</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, displayPrint: 'none' }}>
                    Chạm hoặc rê chuột vào một dòng để khoanh đốm đó trên ảnh.
                  </Typography>
                  <LesionTable lesions={lesions} leafArea={diagnosis.leaf_area_px}
                    highlighted={highlighted} onHighlight={setHighlighted} />
                </Box>
              )}
            </CardContent>
          </Card>
        </Box>
        <Box sx={{ order: { xs: 1, md: 2 }, minWidth: 0 }}>{summary}</Box>
      </Box>

      {(withSeverityAdvice || hasDiseaseAdvice) && (
        <Box sx={{
          display: 'grid', gap: 3, alignItems: 'start',
          gridTemplateColumns: { xs: '1fr', md: withSeverityAdvice && hasDiseaseAdvice ? '5fr 7fr' : '1fr' },
        }}>
          {withSeverityAdvice && (
            <Card sx={{ borderTop: 4, borderTopColor: level?.color ?? 'divider' }}>
              <CardContent sx={CARD_CONTENT_SX}>
                <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', mb: 2 }}>
                  <Box sx={{
                    width: 40, height: 40, borderRadius: '10px', flexShrink: 0, display: 'grid', placeItems: 'center',
                    bgcolor: alpha(level?.color ?? '#000', 0.12), color: level?.color,
                  }}>
                    <HealthAndSafetyOutlinedIcon />
                  </Box>
                  <Box>
                    <Typography variant="overline" color="text.secondary" component="p" sx={{ lineHeight: 1.4 }}>
                      Khuyến nghị IPM theo cấp độ
                    </Typography>
                    <Typography variant="h6" component="h2" sx={{ lineHeight: 1.3 }}>{level?.label}</Typography>
                  </Box>
                </Stack>
                <Typography sx={{ lineHeight: 1.7 }}>{diagnosis.recommendation}</Typography>
              </CardContent>
            </Card>
          )}
          <DiseaseRecommendation disease={disease} recommendation={diseaseAdvice} />
        </Box>
      )}

      {diagnosis.steps?.length > 0 && (
        <Card>
          <CardContent sx={CARD_CONTENT_SX}>
            <Typography variant="h6" component="h2">Các bước xử lý ảnh</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
              {diagnosis.steps.length} ảnh trung gian của quy trình xử lý. Bấm vào ảnh để xem lớn.
            </Typography>
            <StepGallery steps={diagnosis.steps} />
          </CardContent>
        </Card>
      )}

      {histogramImages.every(Boolean) && (
        <Card sx={{ breakInside: 'avoid' }}>
          <CardContent sx={CARD_CONTENT_SX}>
            <Typography variant="h6" component="h2">Histogram độ sáng trước và sau CLAHE</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Phân bố kênh L* (CIELAB) của ảnh sau khử nhiễu và sau cân bằng sáng CLAHE, tính trên toàn ảnh 512×512.
            </Typography>
            <ClaheHistogram beforeUrl={histogramImages[0]} afterUrl={histogramImages[1]} />
          </CardContent>
        </Card>
      )}
    </Stack>
  );
}
