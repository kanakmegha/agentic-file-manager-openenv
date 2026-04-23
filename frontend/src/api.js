// Centralized API Base URL
// In production, we use the relative /api prefix which is handled by vercel.json rewrites.
const BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '/api' : 'http://localhost:8000');

export default BASE_URL;
