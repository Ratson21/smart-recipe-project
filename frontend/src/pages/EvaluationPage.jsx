import { useEffect, useState } from 'react'
import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts'
import api from '../api/axios'
import Navbar from '../components/Navbar'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

// Status colors, not categorical: they encode pass/fail state. Validated
// against a light surface (chroma floor, CVD separation ΔE 13.1 deutan,
// contrast >= 3:1). Status is never carried by color alone - every chart bar
// has a legend and every table row states its verdict in words.
const PASS = '#0d9488'
const FAIL = '#dc2626'

// Verdict palette. A TF-IDF win is not "failure", so it gets its own amber
// rather than the red used for missed expectations - the two mean different
// things and must not read as the same signal.
const WINNER_TONE = {
  Sistem:   { fg: '#0d9488', bg: '#f0fdfa', border: '#ccfbf1' },
  'TF-IDF': { fg: '#b45309', bg: '#fffbeb', border: '#fde68a' },
  Seri:     { fg: '#4b5563', bg: '#f9fafb', border: '#e5e7eb' },
}
const NEUTRAL_TONE = WINNER_TONE.Seri

const CATEGORY_ORDER = ['biasa', 'sinonim']
const CATEGORY_META = {
  biasa: {
    label: 'Biasa',
    desc:  'Ejaan baku',
    badge: 'bg-gray-100 text-gray-600',
    help:  'Semua bahan ditulis dengan nama bakunya.',
  },
  sinonim: {
    label: 'Sinonim',
    desc:  'Kata lain, makna sama',
    badge: 'bg-violet-100 text-violet-700',
    help:  'Satu bahan ditulis dengan kata lain bermakna sama - "seafood" untuk ikan, "telor" untuk telur, "toge" untuk tauge, "unggas" untuk ayam, "sayuran hijau" untuk bayam. Menguji lapisan normalisasi sinonim.',
  },
}

function ScoreCard({ label, value, expected, expectedLabel, met, decimals = 4 }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-card p-5">
      <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-3">{label}</p>
      <p className="font-display text-3xl font-extrabold text-gray-900 leading-none">
        {value.toFixed(decimals)}
      </p>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-[11px] text-gray-400">{expectedLabel}</span>
        <span className="font-mono text-xs text-gray-600">{expected.toFixed(decimals)}</span>
      </div>
      {met !== undefined && (
        <p className="mt-2 text-xs font-semibold" style={{ color: met ? PASS : FAIL }}>
          {met ? '✓ Melewati ekspektasi' : '✗ Belum mencapai ekspektasi'}
        </p>
      )}
    </div>
  )
}

const ChartTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-lg px-4 py-3 text-xs max-w-[260px]">
      <p className="font-semibold text-gray-700 mb-2">{d.full}</p>
      <div className="space-y-1 text-gray-600">
        <div className="flex justify-between gap-4">
          <span>P@5 aktual</span><span className="font-mono font-bold text-gray-900">{d.actual.toFixed(2)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>P@5 ekspektasi</span><span className="font-mono">{d.expected.toFixed(2)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span>Ground truth</span><span className="font-mono">{d.gt} resep</span>
        </div>
      </div>
      <p className="mt-2 pt-2 border-t border-gray-100 font-semibold"
         style={{ color: d.met ? PASS : FAIL }}>
        {d.met ? 'Melewati ekspektasi' : 'Belum mencapai ekspektasi'}
      </p>
    </div>
  )
}

export default function EvaluationPage() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  function load() {
    setLoading(true)
    setError('')
    api.get('/evaluation/metrics')
      .then(r => setData(r.data))
      .catch(err => {
        if (!err.response) setError('Tidak dapat terhubung ke server. Periksa koneksi internet kamu.')
        else if (err.response.status >= 500) setError('Server sedang bermasalah. Silakan coba beberapa saat lagi.')
        else setError('Gagal memuat data evaluasi. Pastikan server berjalan.')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const chartData = data?.per_query?.map(q => ({
    query:    q.query.split(',').slice(0, 2).map(s => s.trim()).join(', '),
    full:     q.query,
    actual:   q.precision_at_5,
    expected: q.expected_precision_at_5,
    gt:       q.ground_truth_size,
    met:      q.meets_precision_target,
  })) ?? []

  const failed = data?.per_query?.filter(q => !q.meets_precision_target) ?? []
  const winnerTone = WINNER_TONE[data?.winner_by_precision_at_5] ?? NEUTRAL_TONE

  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      <main className="max-w-6xl mx-auto px-5 sm:px-6 py-10 pb-20">

        {/* Heading */}
        <div className="mb-10">
          <p className="text-[11px] font-semibold text-teal-700 uppercase tracking-wider mb-1">Evaluasi</p>
          <h1 className="font-display text-3xl font-extrabold text-gray-900">Akurasi Sistem Rekomendasi</h1>
          <p className="text-sm text-gray-500 mt-1.5 max-w-2xl">
            Mengukur tingkat akurasi sistem dalam menghasilkan rekomendasi resep yang relevan
            berdasarkan input bahan makanan pengguna, menggunakan metrik Precision@5 dan Recall@5,
            dengan baseline TF-IDF sebagai pembanding.
          </p>
        </div>

        {loading && <LoadingSpinner size="page" label="Menjalankan evaluasi..." />}
        {error && <ErrorMessage variant="page" message={error} onRetry={load} />}

        {data && (
          <>
            {/* Summary banner */}
            <div className="bg-gray-900 rounded-3xl p-6 sm:p-8 text-white mb-6 shadow-pop">
              <div className="flex flex-wrap items-center gap-x-10 gap-y-6">
                <div>
                  <p className="text-[11px] text-gray-400 uppercase tracking-wider mb-1">Test set</p>
                  <p className="font-display text-2xl font-extrabold">
                    {data.test_set_size} <span className="text-sm text-gray-400 font-medium">query</span>
                  </p>
                </div>
                <div>
                  <p className="text-[11px] text-gray-400 uppercase tracking-wider mb-1">Nilai K</p>
                  <p className="font-display text-2xl font-extrabold">K = {data.k}</p>
                </div>
                <div>
                  <p className="text-[11px] text-gray-400 uppercase tracking-wider mb-1">Waktu evaluasi</p>
                  <p className="font-display text-2xl font-extrabold">{data.elapsed_seconds?.toFixed(2)}s</p>
                </div>
                <div className="ml-auto">
                  <p className="text-[11px] text-gray-400 uppercase tracking-wider mb-1.5">Melewati ekspektasi</p>
                  <p className="font-display text-2xl font-extrabold">
                    {data.queries_meeting_both}
                    <span className="text-sm text-gray-400 font-medium"> / {data.test_set_size} query</span>
                  </p>
                </div>
              </div>
            </div>

            {/* Headline metrics */}
            <div className="grid sm:grid-cols-3 gap-4 mb-6">
              <ScoreCard
                label="Rata-rata Precision@5"
                value={data.avg_precision_at_5}
                expected={data.target_precision_at_5}
                expectedLabel="Ekspektasi ≥"
                met={data.avg_precision_at_5 >= data.target_precision_at_5}
              />
              <ScoreCard
                label="Rata-rata Recall@5"
                value={data.avg_recall_at_5}
                expected={data.avg_expected_recall_at_5}
                expectedLabel="Ekspektasi ≥"
                met={data.avg_recall_at_5 >= data.avg_expected_recall_at_5}
              />
              <ScoreCard
                label="F1-macro"
                value={data.f1_macro}
                expected={data.target_ratio}
                expectedLabel="Rasio target"
                decimals={4}
              />
            </div>

            {/* System vs baseline */}
            {data.baseline_tfidf && (
              <div className="bg-white rounded-2xl border border-gray-200 shadow-card p-5 sm:p-6 mb-6">
                <h2 className="text-sm font-bold text-gray-900">Perbandingan dengan Baseline TF-IDF</h2>

                {/* Verdict */}
                <div
                  className="mt-3 mb-4 rounded-xl px-4 py-3 flex flex-wrap items-center gap-x-8 gap-y-3"
                  style={{ background: winnerTone.bg, border: `1px solid ${winnerTone.border}` }}
                >
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-0.5">
                      Unggul pada Precision@5
                    </p>
                    <p className="font-display text-xl font-extrabold leading-none" style={{ color: winnerTone.fg }}>
                      {data.winner_by_precision_at_5}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-0.5">Selisih</p>
                    <p className="font-mono text-lg font-bold leading-none" style={{ color: winnerTone.fg }}>
                      {data.precision_margin_at_5 >= 0 ? '+' : ''}{data.precision_margin_at_5?.toFixed(4)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-0.5">
                      Rekor per query
                    </p>
                    <p className="text-sm font-semibold text-gray-700 leading-none">
                      {data.queries_system_wins} menang · {data.queries_tie} seri · {data.queries_tfidf_wins} kalah
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-0.5">
                      Unggul pada F1-macro
                    </p>
                    <p className="text-sm font-semibold leading-none" style={{ color: winnerTone.fg }}>
                      {data.winner_by_f1_macro}
                    </p>
                  </div>
                </div>

                <p className="text-xs text-gray-500 mt-1 mb-4 max-w-3xl leading-relaxed">
                  Baseline menerima <strong>query mentah apa adanya</strong>, sedangkan sistem melewati
                  lapisan query understanding lebih dulu (normalisasi sinonim, koreksi typo, gating
                  bahan luar-domain). Jadi yang dibandingkan adalah <strong>sistem utuh</strong> terhadap
                  pencarian leksikal standar - bukan Sentence Transformer melawan TF-IDF sebagai metode
                  murni. Pada subset sinonim, ground truth memakai nama bahan kanonik sementara baseline
                  hanya melihat ejaan yang diketik, sehingga skornya rendah <em>secara struktural</em>.
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Metode</th>
                        <th className="text-center px-3 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">P@5</th>
                        <th className="text-center px-3 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">R@5</th>
                        <th className="text-center px-3 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">F1-macro</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      <tr>
                        <td className="px-4 py-3 font-semibold text-gray-800">Sistem (Sentence Transformer + Weighted)</td>
                        <td className="px-3 py-3 text-center font-mono text-xs font-bold text-gray-900">{data.avg_precision_at_5.toFixed(4)}</td>
                        <td className="px-3 py-3 text-center font-mono text-xs text-gray-700">{data.avg_recall_at_5.toFixed(4)}</td>
                        <td className="px-3 py-3 text-center font-mono text-xs text-gray-700">{data.f1_macro.toFixed(4)}</td>
                      </tr>
                      <tr>
                        <td className="px-4 py-3 text-gray-600">Baseline TF-IDF (query mentah)</td>
                        <td className="px-3 py-3 text-center font-mono text-xs text-gray-700">{data.baseline_tfidf.avg_precision_at_5.toFixed(4)}</td>
                        <td className="px-3 py-3 text-center font-mono text-xs text-gray-700">{data.baseline_tfidf.avg_recall_at_5.toFixed(4)}</td>
                        <td className="px-3 py-3 text-center font-mono text-xs text-gray-700">{data.baseline_tfidf.f1_macro.toFixed(4)}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p className="text-xs text-gray-400 mt-3 pt-3 border-t border-gray-100">
                  Baseline tidak diberi ekspektasi - ia titik acuan, bukan sistem kedua yang juga
                  harus lulus. Verdict &ldquo;unggul&rdquo; ditentukan dari Precision@5 yang dibulatkan,
                  sehingga selalu sesuai dengan angka yang tertera di sebelahnya.
                </p>
              </div>
            )}

            {/* Per-query precision vs threshold */}
            <div className="bg-white rounded-2xl border border-gray-200 shadow-card p-5 sm:p-6 mb-6">
              <div className="flex flex-wrap items-start justify-between gap-4 mb-5">
                <div>
                  <h2 className="text-sm font-bold text-gray-900">Precision@5 per Query</h2>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Garis putus-putus adalah ekspektasi ({data.target_precision_at_5.toFixed(2)}) -
                    sama untuk semua query, karena itulah ia digambar sebagai garis acuan, bukan batang kedua.
                  </p>
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-600">
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-sm inline-block" style={{ background: PASS }} />
                    Melewati ekspektasi
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 rounded-sm inline-block" style={{ background: FAIL }} />
                    Belum mencapai
                  </span>
                </div>
              </div>
              <ResponsiveContainer width="100%" height={430}>
                <BarChart
                  data={chartData}
                  layout="vertical"
                  margin={{ top: 0, right: 24, left: 0, bottom: 0 }}
                  barCategoryGap="22%"
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                  <XAxis
                    type="number" domain={[0, 1]} tickCount={6}
                    tick={{ fontSize: 11, fill: '#9ca3af' }} tickLine={false} axisLine={false}
                  />
                  <YAxis
                    type="category" dataKey="query" width={130}
                    tick={{ fontSize: 10, fill: '#6b7280' }} tickLine={false} axisLine={false}
                  />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: '#f9fafb' }} />
                  <ReferenceLine
                    x={data.target_precision_at_5}
                    stroke="#374151" strokeDasharray="4 4" strokeWidth={2}
                    label={{
                      value: `ekspektasi ${data.target_precision_at_5.toFixed(2)}`,
                      position: 'top', fontSize: 10, fill: '#374151',
                    }}
                  />
                  <Bar dataKey="actual" radius={[0, 4, 4, 0]} maxBarSize={13}>
                    {chartData.map((d, i) => (
                      <Cell key={i} fill={d.met ? PASS : FAIL} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              {failed.length > 0 && (
                <p className="text-xs text-gray-500 mt-4 pt-4 border-t border-gray-100">
                  <strong className="text-gray-700">Belum mencapai ekspektasi:</strong>{' '}
                  {failed.map(q => `“${q.query}” (P@5 ${q.precision_at_5.toFixed(2)})`).join('; ')}.
                </p>
              )}
            </div>

            {/* Per-subset */}
            {data.by_category && (
              <div className="bg-white rounded-2xl border border-gray-200 shadow-card overflow-hidden mb-6">
                <div className="px-5 py-4 border-b border-gray-100">
                  <h2 className="text-sm font-bold text-gray-900">Hasil per Subset</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Subset</th>
                        <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Query</th>
                        <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">P@5</th>
                        <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">R@5</th>
                        <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">F1</th>
                        <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide border-l border-gray-200">P@5 TF-IDF</th>
                        <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Unggul</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {CATEGORY_ORDER.filter(c => data.by_category[c]).map(c => {
                        const b = data.by_category[c]
                        const meta = CATEGORY_META[c]
                        return (
                          <tr key={c} className="hover:bg-gray-50 transition-colors">
                            <td className="px-5 py-3">
                              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${meta.badge}`}>
                                {meta.label}
                              </span>
                              <span className="block text-xs text-gray-400 mt-1">{meta.desc}</span>
                            </td>
                            <td className="px-3 py-3 text-center text-xs text-gray-500">{b.n}</td>
                            <td className="px-3 py-3 text-center font-mono text-xs text-gray-700">{b.avg_precision_at_5.toFixed(4)}</td>
                            <td className="px-3 py-3 text-center font-mono text-xs text-gray-700">{b.avg_recall_at_5.toFixed(4)}</td>
                            <td className="px-3 py-3 text-center font-mono text-xs text-gray-700">{b.f1_macro.toFixed(4)}</td>
                            <td className="px-3 py-3 text-center font-mono text-xs text-gray-500 border-l border-gray-200">
                              {b.tfidf ? b.tfidf.avg_precision_at_5.toFixed(4) : '-'}
                            </td>
                            <td className="px-3 py-3 text-center">
                              {b.winner ? (
                                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                                      style={{
                                        color: (WINNER_TONE[b.winner] ?? NEUTRAL_TONE).fg,
                                        background: (WINNER_TONE[b.winner] ?? NEUTRAL_TONE).bg,
                                      }}>
                                  {b.winner}
                                </span>
                              ) : <span className="text-xs text-gray-300">-</span>}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
                <div className="px-5 py-4 border-t border-gray-100 bg-gray-50 space-y-2.5">
                  {CATEGORY_ORDER.filter(c => data.by_category[c]).map(c => (
                    <div key={c} className="flex gap-2.5 items-start">
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0 mt-px ${CATEGORY_META[c].badge}`}>
                        {CATEGORY_META[c].label}
                      </span>
                      <p className="text-xs text-gray-500">{CATEGORY_META[c].help}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Expectation vs result */}
            <div className="bg-white rounded-2xl border border-gray-200 shadow-card overflow-hidden mb-6">
              <div className="px-5 py-4 border-b border-gray-100">
                <h2 className="text-sm font-bold text-gray-900">Detail Per Query - Ekspektasi vs Hasil</h2>
                <p className="text-xs text-gray-400 mt-0.5 max-w-2xl">
                  Kolom ekspektasi berlatar abu-abu, kolom hasil berlatar putih.
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th colSpan={2} className="px-5 py-2 text-left text-[10px] font-bold text-gray-400 uppercase tracking-wider">Query</th>
                      <th colSpan={3} className="px-3 py-2 text-center text-[10px] font-bold text-gray-500 uppercase tracking-wider bg-gray-100 border-x border-gray-200">Ekspektasi</th>
                      <th colSpan={4} className="px-3 py-2 text-center text-[10px] font-bold text-gray-500 uppercase tracking-wider">Hasil Sistem</th>
                      <th colSpan={3} className="px-3 py-2 text-center text-[10px] font-bold text-gray-500 uppercase tracking-wider border-l border-gray-200">Baseline TF-IDF</th>
                    </tr>
                    <tr className="bg-gray-50">
                      <th className="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Query</th>
                      <th className="text-left px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Subset</th>
                      <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide bg-gray-100 border-l border-gray-200">GT</th>
                      <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide bg-gray-100">P@5</th>
                      <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide bg-gray-100 border-r border-gray-200">R@5</th>
                      <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">GT</th>
                      <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">P@5</th>
                      <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">R@5</th>
                      <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Status</th>
                      <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide border-l border-gray-200">P@5</th>
                      <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">R@5</th>
                      <th className="text-center px-3 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Unggul</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {data.per_query.map((q, i) => {
                      const ok = q.meets_precision_target && q.meets_recall_target && q.gt_within_expected
                      return (
                        <tr key={i} className="hover:bg-gray-50 transition-colors">
                          <td className="px-5 py-3 text-gray-700 max-w-[190px] truncate font-medium" title={q.query}>{q.query}</td>
                          <td className="px-3 py-3">
                            {CATEGORY_META[q.category] && (
                              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${CATEGORY_META[q.category].badge}`}>
                                {CATEGORY_META[q.category].label}
                              </span>
                            )}
                          </td>

                          {/* Ekspektasi */}
                          <td className="px-3 py-3 text-center font-mono text-xs text-gray-500 bg-gray-50 border-l border-gray-200 whitespace-nowrap">
                            {q.expected_gt_min}-{q.expected_gt_max}
                          </td>
                          <td className="px-3 py-3 text-center font-mono text-xs text-gray-500 bg-gray-50">
                            ≥ {q.expected_precision_at_5.toFixed(2)}
                          </td>
                          <td className="px-3 py-3 text-center font-mono text-xs text-gray-500 bg-gray-50 border-r border-gray-200">
                            ≥ {q.expected_recall_at_5.toFixed(4)}
                          </td>

                          {/* Hasil */}
                          <td className="px-3 py-3 text-center">
                            <span className="font-mono text-xs" style={{ color: q.gt_within_expected ? '#4b5563' : FAIL }}>
                              {q.ground_truth_size}
                            </span>
                          </td>
                          <td className="px-3 py-3 text-center">
                            <span className="font-mono text-xs font-semibold px-2 py-1 rounded-full"
                                  style={{
                                    color: q.meets_precision_target ? PASS : FAIL,
                                    background: q.meets_precision_target ? '#ccfbf1' : '#fee2e2',
                                  }}>
                              {q.precision_at_5.toFixed(2)}
                            </span>
                          </td>
                          <td className="px-3 py-3 text-center">
                            <span className="font-mono text-xs" style={{ color: q.meets_recall_target ? '#4b5563' : FAIL }}>
                              {q.recall_at_5.toFixed(4)}
                            </span>
                          </td>
                          <td className="px-3 py-3 text-center text-xs whitespace-nowrap font-semibold"
                              style={{ color: ok ? PASS : FAIL }}>
                            {ok ? 'Lulus' : (!q.gt_within_expected ? 'GT di luar' : 'Belum')}
                          </td>

                          {/* Baseline - measured only, deliberately unstyled by verdict */}
                          <td className="px-3 py-3 text-center font-mono text-xs text-gray-500 border-l border-gray-200">
                            {q.tfidf_precision_at_5?.toFixed(2) ?? '-'}
                          </td>
                          <td className="px-3 py-3 text-center font-mono text-xs text-gray-500">
                            {q.tfidf_recall_at_5?.toFixed(4) ?? '-'}
                          </td>
                          <td className="px-3 py-3 text-center whitespace-nowrap">
                            {q.winner ? (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                                    style={{
                                      color: (WINNER_TONE[q.winner] ?? NEUTRAL_TONE).fg,
                                      background: (WINNER_TONE[q.winner] ?? NEUTRAL_TONE).bg,
                                    }}>
                                {q.winner}
                              </span>
                            ) : <span className="text-xs text-gray-300">-</span>}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              <div className="px-5 py-3 border-t border-gray-100 bg-gray-50">
                <p className="text-xs text-gray-400">
                  Melewati ekspektasi Precision@5:{' '}
                  <strong className="text-gray-600">{data.queries_meeting_precision_target}/{data.test_set_size}</strong>
                  {' '}· Recall@5:{' '}
                  <strong className="text-gray-600">{data.queries_meeting_recall_target}/{data.test_set_size}</strong>
                  {' '}· Ground truth dalam rentang:{' '}
                  <strong className="text-gray-600">{data.gt_within_expected_count}/{data.test_set_size}</strong>.
                </p>
              </div>
            </div>

            {/* Methodology */}
            <div className="bg-white rounded-2xl border border-gray-200 shadow-card p-6 sm:p-8">
              <h2 className="text-sm font-bold text-gray-900 mb-4">Metodologi Evaluasi</h2>
              <div className="grid sm:grid-cols-2 gap-6 text-sm text-gray-600">
                <div className="space-y-3">
                  <div>
                    <p className="font-semibold text-gray-800 mb-1">Precision@5</p>
                    <p className="font-mono text-xs bg-gray-50 rounded-lg px-3 py-2 text-gray-700 mb-1">
                      P@5 = relevan_di_top_5 / 5
                    </p>
                    <p className="text-xs text-gray-500">
                      Proporsi resep relevan dalam 5 hasil teratas. Ekspektasi ditetapkan
                      ≥ {data.target_precision_at_5.toFixed(2)} - minimal 4 dari 5 hasil teratas relevan -
                      seragam untuk semua query agar tidak disesuaikan ke hasil pengukuran.
                    </p>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-800 mb-1">Recall@5</p>
                    <p className="font-mono text-xs bg-gray-50 rounded-lg px-3 py-2 text-gray-700 mb-1">
                      R@5 = relevan_di_top_5 / total_relevan
                    </p>
                    <p className="text-xs text-gray-500">
                      Ekspektasi Recall@5 <strong>tidak bisa berupa angka tetap</strong>: plafonnya
                      ditentukan ukuran ground truth. Query dengan GT 1.089 resep mustahil melampaui
                      5/1.089 ≈ 0,0046, sedangkan GT 8 bisa mencapai 0,625. Karena itu ekspektasinya
                      ditetapkan relatif - {(data.target_ratio * 100).toFixed(0)}% dari plafon
                      min(5, GT)/GT.
                    </p>
                  </div>
                </div>
                <div className="space-y-3">
                  <div>
                    <p className="font-semibold text-gray-800 mb-1">Ground Truth</p>
                    <p className="text-xs text-gray-500">
                      Sebuah resep relevan bila mengandung <strong>SEMUA bahan inti</strong> query
                      (full-match, word-boundary regex). Bumbu dasar - garam, kecap, lada, saos,
                      kaldu - dikecualikan: bumbu muncul di mayoritas resep (garam ada di 12.284 dari
                      14.945 resep), sehingga mengikutsertakannya membuat relevansi mengukur cara
                      membumbui, bukan hidangannya. Sistem sendiri sudah memperlakukannya begitu -
                      INGREDIENT_WEIGHTS memberi bumbu dasar bobot 0,3-0,5 berbanding 2,5-3,0 untuk
                      bahan pokok.
                    </p>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-800 mb-1">Test Set</p>
                    <p className="text-xs text-gray-500">
                      {data.test_set_size} query dalam dua subset: <strong>biasa</strong> (15) dan
                      <strong> sinonim</strong> (5). Setiap query memuat minimal 3 bahan dengan
                      sedikitnya 1 bahan pokok, dan minimal 2 bahan inti setelah bumbu dikeluarkan -
                      dengan 1 bahan inti, P@5 otomatis 1,00 dan berhenti membedakan.
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-5 pt-5 border-t border-gray-100 space-y-2">
                <p className="text-xs text-gray-400">
                  <strong className="text-gray-500">Jalur yang diukur:</strong> evaluasi memakai jalur
                  yang sama dengan yang dialami pengguna - normalisasi sinonim, koreksi ejaan, dan
                  gating bahan di luar domain, lalu pencarian semantik.
                </p>
                <p className="text-xs text-gray-400">
                  <strong className="text-gray-500">Catatan:</strong> status Recall@5 tidak independen
                  dari Precision@5. Untuk GT ≥ 5 berlaku R@5 = P@5 × 5/GT, sehingga mencapai{' '}
                  {(data.target_ratio * 100).toFixed(0)}% plafon recall adalah kondisi yang sama persis
                  dengan mencapai P@5 ≥ {data.target_precision_at_5.toFixed(2)}. Recall@5 dilaporkan
                  untuk nilai absolutnya, bukan sebagai pengujian kedua yang terpisah.
                </p>
                <p className="text-xs text-gray-400">
                  <strong className="text-gray-500">Batasan:</strong> subset <em>sinonim</em>
                  {' '}diselesaikan kamus normalisasi leksikal sebelum teks mencapai encoder, jadi subset
                  ini membuktikan bekerjanya lapisan normalisasi - belum generalisasi semantik oleh
                  Sentence Transformer itu sendiri.
                </p>
              </div>
            </div>
          </>
        )}

      </main>
    </div>
  )
}
