export interface Article {
  id: string;
  title: string;
  summary?: string;
  url: string;
  mediaOutlet: string;
  category: string;
  publishedAt: string;
  bias: 'left' | 'center' | 'right';
} 