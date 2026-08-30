import Navbar from '../components/Navbar'

const STEPS = [
  {
    number: '01',
    icon: '🥬',
    title: 'Input Bahan',
    subtitle: 'Ketik bahan yang kamu punya',
    color: 'from-green-50 to-emerald-50',
    borderColor: 'border-green-200',
    numberColor: 'text-green-200',
    tagColor: 'bg-green-100 text-green-700',
    description:
      'Tuliskan bahan makanan yang tersedia di dapur - pisahkan dengan koma. Tidak perlu urut atau lengkap.',
    details: [
      { label: 'Contoh input', value: 'ayam, bawang putih, tomat, cabai' },
      { label: 'Format', value: 'Nama bahan, dipisah koma' },
      { label: 'Filter opsional', value: 'Kesulitan, waktu masak' },
    ],
    tag: 'Natural Language Input',
  },
  {
    number: '02',
    icon: '🤖',
    title: 'Proses AI',
    subtitle: 'Query Understanding + Weighted Encoding',
    color: 'from-blue-50 to-indigo-50',
    borderColor: 'border-blue-200',
    numberColor: 'text-blue-200',
    tagColor: 'bg-blue-100 text-blue-700',
    description:
      'Input dibersihkan lebih dulu (koreksi typo, sinonim, buang bahan di luar dataset), lalu setiap bahan diubah menjadi vektor 384 dimensi. Bobot berbeda diterapkan sesuai peran bahan dalam masakan.',
    pipeline: [
      { step: 'Query Understanding', desc: 'Koreksi typo (ayma->ayam), sinonim (telor->telur), buang bahan luar-domain' },
      { step: 'Tokenisasi', desc: 'Input dipecah per bahan (split koma)' },
      { step: 'Encoding', desc: 'Setiap bahan -> vektor 384-dim via paraphrase-multilingual-MiniLM-L12-v2' },
      { step: 'Weighting', desc: 'Staple & protein (3×), nabati (2.5×), sayuran (2×), aromatik (1.5×), pelengkap (1×), bumbu dasar (0.5×)' },
      { step: 'Averaging', desc: 'Weighted average -> L2-normalize -> single query vector' },
    ],
    tag: 'Semantic Vector Search',
  },
  {
    number: '03',
    icon: '⚖️',
    title: 'Skoring Relevansi',
    subtitle: 'Semantic + Lexical Coverage',
    color: 'from-amber-50 to-orange-50',
    borderColor: 'border-amber-200',
    numberColor: 'text-amber-200',
    tagColor: 'bg-amber-100 text-amber-700',
    description:
      'Skor kecocokan menggabungkan kemiripan makna (semantic) dengan cakupan bahan yang benar-benar ada di resep (lexical). Lexical mencegah resep satu bahan mengalahkan resep multi-bahan.',
    formula: {
      label: 'Formula skoring relevansi',
      value: 'query_score = 0.65 × semantic + 0.35 × lexical_coverage',
    },
    details: [
      { label: 'Semantic', value: 'Kemiripan makna vektor query vs resep (65%)' },
      { label: 'Lexical coverage', value: 'Fraksi bahan query yang muncul di resep, ditimbang bobot (35%)' },
      { label: 'Tiebreaker', value: 'Skor mirip -> resep dengan bahan lebih sedikit diutamakan' },
    ],
    tag: 'Weighted Hybrid Scoring',
  },
  {
    number: '04',
    icon: '✨',
    title: 'Rekomendasi Personal',
    subtitle: 'Hybrid Scoring berdasarkan selera',
    color: 'from-purple-50 to-fuchsia-50',
    borderColor: 'border-purple-200',
    numberColor: 'text-purple-200',
    tagColor: 'bg-purple-100 text-purple-700',
    description:
      'Bila kamu login dan punya riwayat, skor relevansi digabung dengan profil selera pribadi dari resep yang kamu rating ≥4 dan bookmark.',
    formula: {
      label: 'Formula hybrid scoring',
      value: 'hybrid = 0.7 × query_score + 0.3 × taste_score',
    },
    details: [
      { label: 'Query score', value: 'Skor relevansi bahan (semantic + lexical) - 70%' },
      { label: 'Taste score', value: 'Kemiripan dengan riwayat & bookmark - 30%' },
      { label: 'Cold start', value: '100% query score (belum ada riwayat)' },
    ],
    tag: 'Hybrid Recommendation',
  },
]

const TECH_STATS = [
  { value: '14.945', label: 'Resep Indonesia', icon: '🍳' },
  { value: '384', label: 'Dimensi vektor', icon: '📐' },
  { value: '96%', label: 'Rata-rata Precision@5', icon: '🎯' },
]

export default function HowItWorksPage() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      <main className="max-w-4xl mx-auto px-5 sm:px-6 py-14 pb-20">

        {/* Hero */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-green-700 bg-green-50 ring-1 ring-green-100 px-3 py-1.5 rounded-full mb-5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
            Behind the scenes
          </div>
          <h1 className="font-display text-4xl sm:text-5xl font-extrabold text-gray-900 leading-[1.05] mb-4">
            Cara Kerja Smart Recipe
          </h1>
          <p className="text-gray-500 max-w-xl mx-auto leading-relaxed text-base sm:text-lg">
            Sistem rekomendasi berbasis AI yang memahami <em className="not-italic font-semibold text-gray-700">makna</em> bahan secara semantik -
            bukan sekadar mencocokkan kata.
          </p>
        </div>

        {/* Steps */}
        <div className="space-y-6 mb-16">
          {STEPS.map((s, i) => (
            <div
              key={i}
              className={`relative rounded-2xl bg-gradient-to-br ${s.color} border ${s.borderColor} p-6 sm:p-8 overflow-hidden`}
            >
              <div className={`absolute right-6 top-4 text-8xl font-black ${s.numberColor} select-none leading-none pointer-events-none`}>
                {s.number}
              </div>

              <div className="relative">
                <div className="flex flex-wrap items-start gap-3 mb-4">
                  <span className="text-3xl">{s.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <h2 className="text-xl font-bold text-gray-900">{s.title}</h2>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${s.tagColor}`}>
                        {s.tag}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500">{s.subtitle}</p>
                  </div>
                </div>

                <p className="text-sm text-gray-700 mb-5 leading-relaxed max-w-2xl">
                  {s.description}
                </p>

                {/* Step 1 & 3 details */}
                {s.details && !s.pipeline && !s.formula && (
                  <div className="grid sm:grid-cols-3 gap-3">
                    {s.details.map((d, j) => (
                      <div key={j} className="bg-white/70 rounded-xl px-4 py-3">
                        <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide mb-1">{d.label}</p>
                        <p className="text-sm text-gray-800 font-medium">{d.value}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Step 2: pipeline */}
                {s.pipeline && (
                  <div className="flex flex-col sm:flex-row flex-wrap gap-2">
                    {s.pipeline.map((p, j) => (
                      <div key={j} className="flex items-center gap-2">
                        <div className="bg-white/80 rounded-xl px-4 py-3 w-full sm:w-auto sm:min-w-[160px]">
                          <p className="text-xs font-bold text-gray-700 mb-0.5">{p.step}</p>
                          <p className="text-xs text-gray-500 leading-snug">{p.desc}</p>
                        </div>
                        {j < s.pipeline.length - 1 && (
                          <span className="text-gray-400 text-lg hidden sm:block shrink-0">»</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Step 3: formula + details */}
                {s.formula && (
                  <div className="space-y-3">
                    <div className="bg-white/80 rounded-xl px-5 py-3 font-mono text-sm text-gray-800 border border-purple-100">
                      <span className="text-xs text-gray-400 block mb-1 font-sans">{s.formula.label}</span>
                      {s.formula.value}
                    </div>
                    <div className="grid sm:grid-cols-3 gap-3">
                      {s.details.map((d, j) => (
                        <div key={j} className="bg-white/70 rounded-xl px-4 py-3">
                          <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide mb-1">{d.label}</p>
                          <p className="text-sm text-gray-800 font-medium">{d.value}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Tech stats */}
        <div className="mb-16">
          <h2 className="font-display text-xl font-extrabold text-gray-900 mb-5 text-center">Fakta Teknis</h2>
          <div className="grid grid-cols-3 gap-4">
            {TECH_STATS.map((t, i) => (
              <div key={i} className="bg-white rounded-2xl border border-gray-200 shadow-card p-5 text-center">
                <div className="text-2xl mb-2">{t.icon}</div>
                <div className="font-display text-2xl font-extrabold text-gray-900">{t.value}</div>
                <div className="text-[11px] text-gray-500 mt-1 uppercase tracking-wider font-medium">{t.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Model info */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-card p-6 sm:p-8">
          <p className="text-[11px] font-semibold text-green-700 uppercase tracking-wider mb-1">Tech Stack</p>
          <h2 className="font-display text-xl font-extrabold text-gray-900 mb-5">Model &amp; Arsitektur</h2>
          <div className="grid sm:grid-cols-2 gap-5">
            {[
              { label: 'NLP Model', code: 'paraphrase-multilingual-MiniLM-L12-v2', note: 'Mendukung Bahasa Indonesia secara native' },
              { label: 'Database', code: 'MongoDB + Motor (async)', note: '14.945 resep masakan Indonesia' },
              { label: 'Backend', code: 'FastAPI + Uvicorn (ASGI)', note: 'Async I/O, Pydantic v2 validation' },
            ].map((item, i) => (
              <div key={i}>
                <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">{item.label}</p>
                <p className="text-gray-800 font-mono text-xs bg-gray-50 ring-1 ring-gray-100 rounded-lg px-3 py-2.5">{item.code}</p>
                <p className="text-xs text-gray-500 mt-2 leading-relaxed">{item.note}</p>
              </div>
            ))}
          </div>
        </div>

      </main>
    </div>
  )
}
