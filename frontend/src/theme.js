import { alpha, createTheme } from '@mui/material/styles';

const GREEN = '#1f6f43'; // xanh lá đậm
const TOMATO = '#d64532'; // đỏ cà chua
const INK = '#1c2b22'; // màu chữ chính
const BORDER = '#e3e7df'; // viền card, đường kẻ

const theme = createTheme({
  palette: {
    primary: { main: GREEN, light: '#e7f2ea', dark: '#15542f' },
    secondary: { main: TOMATO },
    background: { default: '#f6f7f2', paper: '#ffffff' },
    text: { primary: INK, secondary: '#5c6b61' },
    divider: BORDER,
  },
  shape: { borderRadius: 14 },
  typography: {
    fontFamily: '"Be Vietnam Pro", "Segoe UI", Roboto, Arial, sans-serif',
    h3: { fontWeight: 700, letterSpacing: '-0.02em' },
    h4: { fontWeight: 700, letterSpacing: '-0.015em' },
    h5: { fontWeight: 700, letterSpacing: '-0.01em' },
    h6: { fontWeight: 600 },
    subtitle1: { fontWeight: 600 },
    subtitle2: { fontWeight: 600 },
    overline: { fontWeight: 600, letterSpacing: '0.08em' },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: { root: { border: `1px solid ${BORDER}` } },
    },
    MuiPaper: {
      styleOverrides: { rounded: { borderRadius: 14 } },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { borderRadius: 10 }, sizeLarge: { padding: '10px 22px' } },
    },
    MuiToggleButton: {
      styleOverrides: { root: { textTransform: 'none', fontWeight: 600 } },
    },
    MuiChip: {
      styleOverrides: { root: { fontWeight: 600 } },
    },
    MuiAlert: {
      styleOverrides: { root: { borderRadius: 12 } },
    },
    MuiTextField: {
      defaultProps: { fullWidth: true },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: { borderRadius: 10, backgroundColor: '#fff' },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: { height: 8, borderRadius: 4, backgroundColor: alpha(GREEN, 0.12) },
        bar: { borderRadius: 4 },
      },
    },
  },
});

export default theme;
