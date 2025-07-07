export interface BiasGauge {
  left: number;   // 좌파 비율(%)
  center: number; // 중도 비율(%)
  right: number;  // 우파 비율(%)
}

export interface Issue {
  id: string;
  title: string;
  summary: string;
  category: string;
  createdAt: string;
  biasGauge: BiasGauge;
} 