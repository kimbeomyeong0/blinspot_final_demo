"use client";
import React, { useState } from "react";
import { useQuery, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fetcher } from "@/lib/fetcher";
import IssueCard from "@/components/IssueCard";
import { Issue } from "@/types/issue";

const queryClient = new QueryClient();

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

function IssuesList() {
  const { data, isLoading, error } = useQuery<Issue[]>({
    queryKey: ["issues"],
    queryFn: () => fetcher<Issue[]>("/api/issues"),
  });

  // 목업 데이터 (API 서버가 없을 때)
  const mock: Issue[] = [
    {
      id: "1",
      title: "최저임금 인상 논란, 경제에 미치는 영향은?",
      summary: "최저임금 인상이 경제 전반에 미치는 영향과 각계의 반응을 분석합니다.",
      category: "경제",
      createdAt: new Date().toISOString(),
      biasGauge: { left: 30, center: 50, right: 20 },
    },
    {
      id: "2",
      title: "총선 D-30, 판세는 어디로?",
      summary: "총선을 한 달 앞두고 각 당의 전략과 판세를 분석합니다.",
      category: "정치",
      createdAt: new Date().toISOString(),
      biasGauge: { left: 40, center: 40, right: 20 },
    },
    {
      id: "3",
      title: "AI 기술, 사회에 미치는 영향은?",
      summary: "AI 기술의 발전이 사회 전반에 미치는 긍정적·부정적 영향.",
      category: "사회",
      createdAt: new Date().toISOString(),
      biasGauge: { left: 20, center: 60, right: 20 },
    },
  ];

  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  // 임시: 기사 수, 대표 기사, 대표 언론사, 트렌드, 키워드, bias 강조 등 추가 정보 목업
  const issues = (data && data.length > 0 ? data.map(toCamelCaseIssue) : mock).map((issue, idx) => ({
    ...issue,
    _articleCount: 7 + idx, // 임시 기사 수
    _articleCountDiff: idx % 2 === 0 ? 2 : -1, // 임시 기사 수 증감
    _isNew: idx === 0, // 첫 번째 이슈만 NEW
    _trend: idx % 2 === 0 ? 'up' : 'down', // 임시 트렌드
    _keywords: ['부동산', '정책'].slice(0, (idx % 2) + 1), // 임시 키워드
    _mainBias: issue.biasGauge.left >= issue.biasGauge.center && issue.biasGauge.left >= issue.biasGauge.right
      ? 'left'
      : issue.biasGauge.center >= issue.biasGauge.right
      ? 'center'
      : 'right',
  }));

  const categories = Array.from(new Set(issues.map(i => i.category)));
  const filteredIssues = selectedCategory ? issues.filter(i => i.category === selectedCategory) : issues;

  if (issues.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400 gap-2">
        <span className="text-3xl">📰</span>
        <span className="font-semibold">새로운 이슈가 곧 도착합니다!</span>
        <span className="text-sm">관심 있는 주제를 기다려주세요.</span>
      </div>
    );
  }

  return (
    <>
      {/* 카테고리 필터 */}
      <div className="flex gap-2 mb-4">
        <button
          className={`px-3 py-1 rounded-full border text-sm font-semibold transition-colors ${selectedCategory === null ? 'bg-blue-500 text-white border-blue-500' : 'bg-white text-gray-500 border-gray-200 hover:bg-blue-50'}`}
          onClick={() => setSelectedCategory(null)}
        >
          전체
        </button>
        {categories.map(cat => (
          <button
            key={cat}
            className={`px-3 py-1 rounded-full border text-sm font-semibold transition-colors ${selectedCategory === cat ? 'bg-blue-500 text-white border-blue-500' : 'bg-white text-gray-500 border-gray-200 hover:bg-blue-50'}`}
            onClick={() => setSelectedCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>
      <div className="flex flex-col gap-4">
        {filteredIssues.map((issue) => (
          <IssueCard
            key={issue.id}
            issue={issue}
            articleCount={issue._articleCount}
            articleCountDiff={issue._articleCountDiff}
            isNew={issue._isNew}
            trend={issue._trend as 'up' | 'down'}
            keywords={issue._keywords}
            mainBias={issue._mainBias as 'left' | 'center' | 'right'}
          />
        ))}
      </div>
    </>
  );
}

export default function HomePage() {
  return (
    <QueryClientProvider client={queryClient}>
      <main className="min-h-screen bg-gray-50 p-4 max-w-md mx-auto">
        <header className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-1">BlindSpot</h1>
          <p className="text-gray-600 text-sm">뉴스 편향성 분석 서비스</p>
        </header>
        <IssuesList />
      </main>
    </QueryClientProvider>
  );
}
