import { Alert, AlertTitle, Box, Button, Typography } from '@mui/material';

import { resultWarnings } from '../constants/diagnosis';

// Khung cảnh báo trên trang Kết quả khi độ tin cậy thấp hoặc tên bệnh mâu thuẫn với cấp độ.
// onReport: mở hộp "Báo kết quả sai" (FeedbackDialog) với tiêu đề gợi ý.
export default function ResultWarning({ diagnosis, onReport }) {
  const warnings = resultWarnings(diagnosis);
  if (warnings.length === 0) return null;

  return (
    <Alert severity="warning">
      <AlertTitle>Kết quả này có thể chưa chính xác</AlertTitle>
      <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
        {warnings.map((warning) => <li key={warning}>{warning}</li>)}
      </Box>
      <Typography variant="body2" sx={{ mt: 1 }}>
        Hãy thử chụp lại một lá rõ nét, đủ sáng, nền đơn giản. Nếu bạn thấy kết quả sai, hãy gửi phản hồi
        để chúng tôi cải thiện mô hình.
      </Typography>
      <Button variant="outlined" color="warning" size="small" onClick={onReport} sx={{ mt: 1.5 }}>
        Báo kết quả sai
      </Button>
    </Alert>
  );
}
