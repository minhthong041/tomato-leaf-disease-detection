import { ImageList, ImageListItem, ImageListItemBar } from '@mui/material';

import { STEP_LABELS } from '../constants/diagnosis';

// Ảnh trung gian của từng bước pipeline, theo thứ tự backend trả về
export default function StepGallery({ steps }) {
  return (
    <ImageList cols={3} gap={8} sx={{ m: 0 }}>
      {steps.map((item, index) => (
        <ImageListItem key={item.step}>
          <img src={item.image} alt={STEP_LABELS[item.step] ?? item.step} loading="lazy" />
          <ImageListItemBar title={`${index + 1}. ${STEP_LABELS[item.step] ?? item.step}`} />
        </ImageListItem>
      ))}
    </ImageList>
  );
}
