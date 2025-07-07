import React from 'react';
import { notFound } from 'next/navigation';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { fetcher } from '@/lib/fetcher';
import IssueDetail from '@/components/IssueDetail';
import { Issue } from '@/types/issue';
import { Article } from '@/types/article';
import IssueDetailClient from '@/components/IssueDetailClient';

// snake_case → camelCase 변환 함수
function toCamelCaseIssue(issue: any): Issue {
  return {
    id: issue.id,
    title: issue.title,
    summary: issue.summary,
    category: issue.category,
    createdAt: issue.created_at,
    biasGauge: {
      left: issue.bias_gauge.left,
      center: issue.bias_gauge.center,
      right: issue.bias_gauge.right,
    },
  };
}
function toCamelCaseArticle(article: any): Article {
  return {
    id: article.id,
    title: article.title,
    summary: article.summary,
    url: article.url,
    mediaOutlet: article.media_outlet,
    category: article.category,
    publishedAt: article.published_at,
    bias: article.bias as 'left' | 'center' | 'right',
  };
}

function getMediaByBias(articles: Article[]) {
  const left = articles.filter(a => a.bias === 'left').map(a => a.mediaOutlet);
  const center = articles.filter(a => a.bias === 'center').map(a => a.mediaOutlet);
  const right = articles.filter(a => a.bias === 'right').map(a => a.mediaOutlet);
  return {
    left: Array.from(new Set(left)),
    center: Array.from(new Set(center)),
    right: Array.from(new Set(right)),
  };
}

function IssueDetailPage({ id }: { id: string }) {
  const { data: issue, isLoading: issueLoading } = useQuery<Issue>({
    queryKey: ['issue', id],
    queryFn: () => fetcher(`/api/issues/${id}`).then(toCamelCaseIssue),
  });
  const { data: articles = [], isLoading: articlesLoading } = useQuery<Article[]>({
    queryKey: ['articles', id],
    queryFn: () => fetcher(`/api/articles/${id}`).then(arr => (arr as any[]).map(toCamelCaseArticle)),
  });

  if (issueLoading || articlesLoading) return <div className="p-8 text-center text-gray-400">로딩 중...</div>;
  if (!issue) return notFound();

  const mediaByBias = getMediaByBias(articles);

  return <IssueDetail issue={issue} articles={articles} mediaByBias={mediaByBias} />;
}

const queryClient = new QueryClient();

export default function Page({ params }: { params: { id: string } }) {
  return <IssueDetailClient id={params.id} />;
}

// SSG용 generateStaticParams (예시)
export async function generateStaticParams() {
  // 실제 배포 시에는 API에서 id 목록을 받아와야 함
  return [];
} 