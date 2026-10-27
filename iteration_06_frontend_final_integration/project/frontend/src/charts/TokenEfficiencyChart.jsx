import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

export default function DatasetSizeChart({ originalBytes, refinedBytes }) {
  const data = [
    { name: 'Original dataset', bytes: originalBytes, fill: '#8B5CF6' },
    { name: 'Refined dataset', bytes: refinedBytes, fill: '#F59E0B' },
  ];
  return <div className="w-full h-64 font-mono text-xs"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}><XAxis dataKey="name" stroke="#64748B" fontSize={11} tickLine={false} /><YAxis stroke="#64748B" fontSize={11} tickLine={false} /><Tooltip contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px', color: '#FFF' }} formatter={(value) => [`${value.toLocaleString()} bytes`, 'File size']} /><Bar dataKey="bytes" radius={[8, 8, 0, 0]} barSize={50}>{data.map((entry, index) => <Cell key={index} fill={entry.fill} />)}</Bar></BarChart></ResponsiveContainer></div>;
}
