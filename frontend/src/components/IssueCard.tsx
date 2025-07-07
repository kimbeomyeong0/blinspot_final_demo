import React from 'react';
import Link from 'next/link';
import { Issue } from '@/types/issue';
import { MdArrowDropUp, MdArrowDropDown } from 'react-icons/md';

interface IssueCardProps {
  issue: Issue;
  articleCount?: number;
  articleCountDiff?: number;
  isNew?: boolean;
  trend?: 'up' | 'down';
  keywords?: string[];
  mainBias?: 'left' | 'center' | 'right';
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

export default function IssueCard({
  issue,
  articleCount,
  articleCountDiff,
  isNew,
  trend,
  keywords,
  mainBias,
}: IssueCardProps) {
  const color = categoryColors[issue.category] || categoryColors.default;
  const date = new Date(issue.createdAt).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric', year: 'numeric' });

  // bias 게이지 계산
  const { left, center, right } = issue.biasGauge;
  const total = left + center + right || 1;
  const leftPct = (left / total) * 100;
  const centerPct = (center / total) * 100;
  const rightPct = (right / total) * 100;

  return (
    <Link href={`/issues/${issue.id}`} className="block group focus:outline-none">
      <div
        className={
          `relative bg-gradient-to-br from-white via-blue-50 to-purple-50 rounded-3xl shadow-md p-6 mb-6 flex flex-col gap-3 transition-all duration-200 border border-gray-100
          hover:shadow-2xl hover:scale-[1.025] active:scale-[0.99]`
        }
        style={{ minHeight: 180 }}
      >
        {/* 상단 정보 바 */}
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 mb-1">
          <span className={`px-2 py-1 rounded text-xs font-semibold ${color}`}>{issue.category}</span>
          <span className="text-xs text-gray-400 font-medium">{date}</span>
          {trend === 'up' && <span className="flex items-center text-green-500 text-xs font-bold ml-1"><MdArrowDropUp size={20}/>증가</span>}
          {trend === 'down' && <span className="flex items-center text-red-500 text-xs font-bold ml-1"><MdArrowDropDown size={20}/>감소</span>}
          {keywords && keywords.length > 0 && (
            <span className="flex gap-1 ml-1">
              {keywords.map((kw) => (
                <span key={kw} className="bg-gray-100 text-gray-500 rounded px-2 py-0.5 text-xs font-medium">#{kw}</span>
              ))}
            </span>
          )}
          {isNew && <span className="ml-1 px-2 py-0.5 rounded-full bg-blue-100 text-blue-600 text-xs font-bold">NEW</span>}
        </div>
        {/* 제목 */}
        <h2 className="text-xl sm:text-2xl font-extrabold text-gray-900 leading-tight group-hover:text-blue-600 transition-colors duration-150 line-clamp-2">
          {issue.title}
        </h2>
        {/* 요약 */}
        <p className="text-gray-500 text-sm sm:text-base font-normal line-clamp-2 mb-1 mt-1">
          {issue.summary}
        </p>
        {/* 기사 수 및 증감 */}
        {typeof articleCount === 'number' && (
          <div className="flex items-center gap-1 text-xs text-gray-400 mt-1 mb-1">
            <span>📰</span>
            <span>총 {articleCount}개 기사</span>
            {typeof articleCountDiff === 'number' && articleCountDiff !== 0 && (
              <span className={articleCountDiff > 0 ? 'text-green-500 flex items-center gap-0.5' : 'text-red-500 flex items-center gap-0.5'}>
                {articleCountDiff > 0 ? <MdArrowDropUp size={18}/> : <MdArrowDropDown size={18}/>} {Math.abs(articleCountDiff)}
              </span>
            )}
          </div>
        )}
        {/* bias 게이지 */}
        <div className="w-full mt-2 mb-1">
          <div className="flex h-5 rounded-full overflow-hidden bg-gray-100 shadow-inner relative transition-all duration-300">
            {/* Left */}
            <div
              className={`h-full flex items-center justify-center text-white text-xs font-bold transition-all duration-300 bg-gradient-to-r ${biasColors.left}`}
              style={{ width: `${leftPct}%`, borderTopLeftRadius: 9999, borderBottomLeftRadius: 9999 }}
            >
              {leftPct > 8 && <span className="pl-2">Left {Math.round(leftPct)}%</span>}
            </div>
            {/* Center */}
            <div
              className={`h-full flex items-center justify-center text-white text-xs font-bold transition-all duration-300 bg-gradient-to-r ${biasColors.center}`}
              style={{ width: `${centerPct}%` }}
            >
              {centerPct > 8 && <span className="pl-2">Center {Math.round(centerPct)}%</span>}
            </div>
            {/* Right */}
            <div
              className={`h-full flex items-center justify-center text-white text-xs font-bold transition-all duration-300 bg-gradient-to-r ${biasColors.right}`}
              style={{ width: `${rightPct}%`, borderTopRightRadius: 9999, borderBottomRightRadius: 9999 }}
            >
              {rightPct > 8 && <span className="pl-2">Right {Math.round(rightPct)}%</span>}
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
} 