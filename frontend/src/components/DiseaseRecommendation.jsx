import LocalFloristIcon from '@mui/icons-material/LocalFlorist';
import { Box, Card, CardContent, Link, Stack, Typography } from '@mui/material';

// Khuyến nghị theo bệnh (disease_recommendation của API, nội dung từ việc 3D) trên trang Kết quả
export default function DiseaseRecommendation({ disease, recommendation }) {
  if (!disease || !recommendation) return null;
  const title = disease.is_healthy ? 'Khuyến nghị cho lá khỏe' : `Khuyến nghị cho ${disease.name}`;

  return (
    <Card>
      <CardContent>
        <Stack spacing={1.5}>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
            <LocalFloristIcon color="primary" />
            <Typography variant="h6" component="h2">{title}</Typography>
          </Stack>
          {recommendation.cause && (
            <Typography><strong>Tác nhân:</strong> {recommendation.cause}</Typography>
          )}
          <Typography>{recommendation.advice}</Typography>
          {recommendation.pesticide_note && (
            <Typography variant="body2" color="text.secondary">{recommendation.pesticide_note}</Typography>
          )}
          <Box>
            <Typography variant="subtitle2">Nguồn tham khảo</Typography>
            <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
              {recommendation.sources.map((source) => (
                <li key={source.url + source.title}>
                  <Link href={source.url} target="_blank" rel="noopener noreferrer" variant="body2">
                    {source.title}
                  </Link>
                </li>
              ))}
            </Box>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}
