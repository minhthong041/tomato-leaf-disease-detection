import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: { main: '#2e7d32' }, // xanh lá
    secondary: { main: '#c62828' }, // đỏ cà chua
    background: { default: '#f6f8f5' },
  },
  shape: { borderRadius: 10 },
});

export default theme;
