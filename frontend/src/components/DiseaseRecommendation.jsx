import LocalFloristIcon from '@mui/icons-material/LocalFlorist';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { Box, Card, CardContent, Link, Stack, Typography } from '@mui/material';

// Khuyến nghị theo bệnh (disease_recommendation của API, nội dung từ việc 3D) trên trang Kết quả
export default function DiseaseRecommendation({ disease, recommendation }) {
  if (!disease || !recommendation) return null;
  const title = disease.is_healthy ? 'Khuyến nghị cho lá khỏe' : `Khuyến nghị cho ${disease.name}`;

  return (
    <Card>
      <CardContent sx={{ p: { xs: 2.5, sm: 3 }, '&:last-child': { pb: { xs: 2.5, sm: 3 } } }}>
        <Stack spacing={2}>
          <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
            <Box sx={{
              width: 40, height: 40, borderRadius: '10px', flexShrink: 0, display: 'grid', placeItems: 'center',
              bgcolor: 'primary.light', color: 'primary.main',
            }}>
              <LocalFloristIcon />
            </Box>
            <Box>
              <Typography variant="overline" color="text.secondary" component="p" sx={{ lineHeight: 1.4 }}>
                Khuyến nghị theo bệnh
              </Typography>
              <Typography variant="h6" component="h2" sx={{ lineHeight: 1.3 }}>{title}</Typography>
            </Box>
          </Stack>
          {recommendation.cause && (
            <Typography><strong>Tác nhân:</strong> {recommendation.cause}</Typography>
          )}
          <Typography sx={{ lineHeight: 1.7 }}>{recommendation.advice}</Typography>
          {recommendation.pesticide_note && (
            <Typography variant="body2" color="text.secondary"
              sx={{ p: 1.5, borderRadius: '8px', bgcolor: 'background.default' }}>
              {recommendation.pesticide_note}
            </Typography>
          )}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 0.5 }}>Nguồn tham khảo</Typography>
            <Stack component="ul" spacing={0.5} sx={{ m: 0, p: 0, listStyle: 'none' }}>
              {recommendation.sources.map((source) => (
                <li key={source.url + source.title}>
                  <Link href={source.url} target="_blank" rel="noopener noreferrer" variant="body2"
                    sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}>
                    {source.title}
                    <OpenInNewIcon sx={{ fontSize: 14 }} />
                  </Link>
                </li>
              ))}
            </Stack>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}
