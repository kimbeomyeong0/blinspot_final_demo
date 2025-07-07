import axios from 'axios';

// API base URL 설정 (환경 변수 사용)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://blinspotfinaldemo-production.up.railway.app';

// axios 인스턴스 생성
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const fetcher = async <T>(url: string): Promise<T> => {
  const response = await api.get<T>(url);
  // plain object로 변환
  return JSON.parse(JSON.stringify(response.data));
}; 