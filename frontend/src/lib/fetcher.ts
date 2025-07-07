import axios from 'axios';

export const fetcher = async <T>(url: string): Promise<T> => {
  const response = await axios.get<T>(url);
  // plain object로 변환
  return JSON.parse(JSON.stringify(response.data));
}; 