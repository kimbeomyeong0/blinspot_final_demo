import React from 'react';

interface BiasGaugeProps {
  left: number;
  center: number;
  right: number;
}

export default function BiasGauge({ left, center, right }: BiasGaugeProps) {
  const total = left + center + right || 1;
  const leftPct = (left / total) * 100;
  const centerPct = (center / total) * 100;
  const rightPct = (right / total) * 100;

  return (
    <div className="w-full my-4">
      <div className="flex h-4 rounded-full overflow-hidden bg-gray-100 shadow-sm">
        <div
          className="bg-blue-400 h-full"
          style={{ width: `${leftPct}%` }}
        />
        <div
          className="bg-green-400 h-full"
          style={{ width: `${centerPct}%` }}
        />
        <div
          className="bg-red-400 h-full"
          style={{ width: `${rightPct}%` }}
        />
      </div>
      <div className="flex justify-between text-xs mt-1 px-1 text-gray-600 font-medium">
        <span className="text-blue-500">Left {Math.round(leftPct)}%</span>
        <span className="text-green-500">Center {Math.round(centerPct)}%</span>
        <span className="text-red-500">Right {Math.round(rightPct)}%</span>
      </div>
    </div>
  );
} 