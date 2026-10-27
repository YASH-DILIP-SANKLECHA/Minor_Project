import React from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function ChangeBreakdownChart({ similarRemoved, conflictsResolved, otherRemoved, retained }) {
  const data = [
    { name: 'Similar content removed', value: similarRemoved, color: '#A855F7' },
    { name: 'Conflicts resolved', value: conflictsResolved, color: '#F59E0B' },
    { name: 'Other removals', value: otherRemoved, color: '#EF4444' },
    { name: 'Content retained', value: retained, color: '#10B981' },
  ].filter((item) => item.value > 0);
  return <div className="w-full h-64 font-mono text-xs"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data} cx="50%" cy="50%" innerRadius={60} outerRadius={85} paddingAngle={4} dataKey="value">{data.map((entry, index) => <Cell key={index} fill={entry.color} />)}</Pie><Tooltip contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px', color: '#FFF' }} formatter={(value) => [`${value.toLocaleString()} statements`, 'Count']} /><Legend verticalAlign="bottom" height={36} /></PieChart></ResponsiveContainer></div>;
}
