'use client';
import React, { useState } from 'react';
import { Issue } from '@/types/issue';
import { Article } from '@/types/article';
import { MdArrowDropUp, MdArrowDropDown } from 'react-icons/md';

interface IssueDetailProps {
  issue: Issue;
  articles: Article[];
  mediaByBias: {
    left: string[];
    center: string[];
    right: string[];
  };
}

const categoryColors: Record<string, string> = {
  정치: 'bg-purple-100 text-purple-700',
  경제: 'bg-orange-100 text-orange-700',
  사회: 'bg-green-100 text-green-700',
  국제: 'bg-blue-100 text-blue-700',
  문화: 'bg-pink-100 text-pink-700',
  default: 'bg-gray-100 text-gray-700',
};
const biasColors = {
  left: 'from-blue-400 to-blue-300',
  center: 'from-green-400 to-green-300',
  right: 'from-red-400 to-red-300',
};
const biasLabelColors = {
  left: 'text-blue-500',
  center: 'text-green-500',
  right: 'text-red-500',
};

function ArticleCard({ article }: { article: Article }) {
  return (
    <a
      href={article.url}
      target="_blank"
      rel="noopener noreferrer"
      className="bg-white rounded-2xl shadow p-4 mb-3 flex gap-3 items-start border border-gray-50 hover:shadow-lg transition-all group cursor-pointer"
      style={{ textDecoration: 'none' }}
    >
      <div className="w-10 h-10 rounded-full flex items-center justify-center bg-gray-100 text-lg font-bold text-gray-500 shrink-0">
        {article.mediaOutlet[0]}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-semibold text-gray-900 text-base line-clamp-1">{article.title}</span>
          <span className={`ml-auto px-2 py-0.5 rounded text-xs font-semibold ${biasLabelColors[article.bias]}`}>{article.bias.charAt(0).toUpperCase() + article.bias.slice(1)}</span>
        </div>
        <p className="text-xs text-gray-500 mb-1 line-clamp-2">{article.summary}</p>
        <span className="text-xs text-blue-500 font-medium group-hover:underline">원문 보기 →</span>
      </div>
    </a>
  );
}

export default function IssueDetail({ issue, articles }: IssueDetailProps) {
  const [showAll, setShowAll] = useState(false);
  const [showFullSummary, setShowFullSummary] = useState(false);
  const biasList = ['left', 'center', 'right'] as const;
  const date = new Date(issue.createdAt).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric', year: 'numeric' });
  // bias 게이지 계산
  const { left, center, right } = issue.biasGauge;
  const total = left + center + right || 1;
  const leftPct = (left / total) * 100;
  const centerPct = (center / total) * 100;
  const rightPct = (right / total) * 100;

  return (
    <div className="relative bg-gradient-to-br from-white via-blue-50 to-purple-50 rounded-3xl shadow-md p-6 mt-4 mb-8 flex flex-col gap-4 transition-all duration-200 border border-gray-100">
      {/* 상단 정보 바 */}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mb-1">
        <span className={`px-2 py-1 rounded text-xs font-semibold ${categoryColors[issue.category] || categoryColors.default}`}>{issue.category}</span>
        <span className="text-xs text-gray-400 font-medium">{date}</span>
      </div>
      {/* 제목 */}
      <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 leading-tight hover:text-blue-600 transition-colors duration-150 line-clamp-2 mb-1">
        {issue.title}
      </h1>
      {/* 요약 */}
      <div className="bg-gray-50 rounded-xl p-4 mb-2 border border-gray-100">
        <div className="font-semibold text-gray-800 mb-1 text-base">이슈 요약</div>
        <div className={`text-gray-500 text-sm mb-1 ${showFullSummary ? '' : 'line-clamp-3'}`}>{issue.summary}</div>
        {issue.summary && issue.summary.length > 80 && (
          <button
            className="text-xs text-blue-500 font-semibold hover:underline mt-1"
            onClick={() => setShowFullSummary(v => !v)}
          >
            {showFullSummary ? '간략히' : '더보기'}
          </button>
        )}
      </div>
      {/* bias 게이지 */}
      <div className="w-full mt-2 mb-2">
        <div className="flex h-6 rounded-full overflow-hidden bg-gray-100 shadow-inner relative transition-all duration-300">
          {/* Left */}
          <div
            className={`h-full flex items-center justify-center text-white text-sm font-bold transition-all duration-300 bg-gradient-to-r ${biasColors.left}`}
            style={{ width: `${leftPct}%`, borderTopLeftRadius: 9999, borderBottomLeftRadius: 9999 }}
          >
            {leftPct > 8 && <span className="pl-2">Left {Math.round(leftPct)}%</span>}
          </div>
          {/* Center */}
          <div
            className={`h-full flex items-center justify-center text-white text-sm font-bold transition-all duration-300 bg-gradient-to-r ${biasColors.center}`}
            style={{ width: `${centerPct}%` }}
          >
            {centerPct > 8 && <span className="pl-2">Center {Math.round(centerPct)}%</span>}
          </div>
          {/* Right */}
          <div
            className={`h-full flex items-center justify-center text-white text-sm font-bold transition-all duration-300 bg-gradient-to-r ${biasColors.right}`}
            style={{ width: `${rightPct}%`, borderTopRightRadius: 9999, borderBottomRightRadius: 9999 }}
          >
            {rightPct > 8 && <span className="pl-2">Right {Math.round(rightPct)}%</span>}
          </div>
        </div>
      </div>
      {/* Media Outlets by Bias (5행 3열 원형 그리드) */}
      <div className="bg-gradient-to-br from-blue-50 via-white to-purple-50 rounded-2xl shadow p-4 mb-4 border border-gray-50">
        <div className="font-extrabold text-lg text-black mb-2 tracking-tight">이슈 편향 분포</div>
        <div className="grid grid-cols-3 gap-0">
          {/* 헤더 */}
          <div className="flex flex-col items-center">
            <div className="mb-2 text-blue-600 font-bold text-base tracking-wide bg-blue-50 px-3 py-1 rounded-full">Left</div>
          </div>
          <div className="flex flex-col items-center">
            <div className="mb-2 text-green-600 font-bold text-base tracking-wide bg-green-50 px-3 py-1 rounded-full">Center</div>
          </div>
          <div className="flex flex-col items-center">
            <div className="mb-2 text-red-600 font-bold text-base tracking-wide bg-red-50 px-3 py-1 rounded-full">Right</div>
          </div>
          {/* 5행 3열 원형 아이콘 */}
          {['left', 'center', 'right'].map((bias) => {
            // 해당 bias 언론사 중복 제거
            const outlets = Array.from(new Set(articles.filter(a => a.bias === bias).map(a => ({
              name: a.mediaOutlet,
              url: a.url,
            }))));
            // 5개 초과 시 +n
            const showOutlets = outlets.slice(0, 5);
            const extraCount = outlets.length - 5;
            // 5행 맞추기
            const cells = Array.from({ length: 5 }, (_, i) => showOutlets[i] || null);
            // 컬럼별 subtle 배경
            const colBg = bias === 'left' ? 'bg-blue-50/60' : bias === 'center' ? 'bg-green-50/60' : 'bg-red-50/60';
            return (
              <div key={bias} className={`flex flex-col items-center gap-3 py-2 rounded-xl ${colBg}`}>
                {cells.map((outlet, rowIdx) =>
                  outlet ? (
                    <a
                      key={outlet.name}
                      href={outlet.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-14 h-14 rounded-full flex items-center justify-center shadow-sm border border-gray-100 bg-white hover:scale-110 hover:shadow-lg transition text-sm font-bold text-gray-700 text-center px-1 tracking-tight"
                      title={outlet.name}
                      style={{ userSelect: 'none', wordBreak: 'keep-all', fontWeight: 600 }}
                    >
                      {outlet.name}
                    </a>
                  ) : (
                    // placeholder
                    <div
                      key={rowIdx}
                      className="w-14 h-14 rounded-full flex items-center justify-center bg-gray-100 opacity-40 border border-gray-100"
                    />
                  )
                )}
                {/* +n 표기 */}
                {extraCount > 0 && (
                  <div className="w-14 h-14 rounded-full flex items-center justify-center bg-blue-400 text-white font-bold text-base mt-1 shadow">
                    +{extraCount}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
      {/* 기사 리스트 */}
      <div className="mt-2">
        <div className="font-semibold text-gray-800 mb-2">관련 기사</div>
        {biasList.map((bias) => {
          const biasArticles = articles.filter((a) => a.bias === bias);
          const showArticles = showAll ? biasArticles : biasArticles.slice(0, 1);
          return (
            <div key={bias} className="mb-2">
              {showArticles.map((article) => (
                <ArticleCard key={article.id} article={article} />
              ))}
            </div>
          );
        })}
        {articles.length > 3 && (
          <button
            className="mt-2 px-4 py-2 rounded-full bg-blue-50 text-blue-700 font-semibold hover:bg-blue-100 transition shadow border border-blue-100"
            onClick={() => setShowAll((v) => !v)}
          >
            {showAll ? '간략히 보기' : '전체 기사 보기'}
          </button>
        )}
      </div>
    </div>
  );
}

// 랜덤 컬러 함수 (같은 이름은 항상 같은 색)
function randomColor(str: string) {
  const colors = ['#60a5fa', '#34d399', '#f87171', '#fbbf24', '#a78bfa', '#f472b6', '#38bdf8', '#facc15'];
  let hash = 0;
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
} 