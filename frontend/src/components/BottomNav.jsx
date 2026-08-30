import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function HomeIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 11l9-8 9 8" /><path d="M5 10v10a1 1 0 001 1h12a1 1 0 001-1V10" /><path d="M10 21v-6h4v6" />
    </svg>
  )
}
function BookmarkIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z" />
    </svg>
  )
}
function HistoryIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
    </svg>
  )
}
function ProfileIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0116 0" />
    </svg>
  )
}
function InfoIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" /><path d="M12 8h.01M11 12h1v4h1" />
    </svg>
  )
}

function TabItem({ to, exact, Icon, label, pathname }) {
  const active = exact ? pathname === to : pathname.startsWith(to)
  return (
    <Link
      to={to}
      className={`relative flex flex-col items-center justify-center flex-1 py-2 gap-1 transition-colors ${
        active ? 'text-green-600' : 'text-gray-400 hover:text-gray-600'
      }`}
    >
      {active && (
        <span className="absolute top-0 left-1/2 -translate-x-1/2 w-10 h-0.5 rounded-full bg-green-500" />
      )}
      <Icon />
      <span className="text-[10px] font-semibold leading-none tracking-wide">{label}</span>
    </Link>
  )
}

export default function BottomNav() {
  const { isLoggedIn } = useAuth()
  const { pathname }   = useLocation()

  const tabs = isLoggedIn
    ? [
        { to: '/',          exact: true, Icon: HomeIcon,     label: 'Beranda' },
        { to: '/bookmarks',             Icon: BookmarkIcon,  label: 'Simpan'  },
        { to: '/history',               Icon: HistoryIcon,   label: 'Riwayat' },
        { to: '/profile',               Icon: ProfileIcon,   label: 'Profil'  },
      ]
    : [
        { to: '/',           exact: true, Icon: HomeIcon,    label: 'Beranda'  },
        { to: '/how-it-works',           Icon: InfoIcon,     label: 'Cara Kerja' },
        { to: '/login',                  Icon: ProfileIcon,  label: 'Masuk'    },
      ]

  return (
    <nav className="sm:hidden fixed bottom-0 left-0 right-0 z-30 bg-white/95 backdrop-blur-md border-t border-gray-200/70"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <div className="flex items-stretch h-16">
        {tabs.map(tab => (
          <TabItem key={tab.to} {...tab} pathname={pathname} />
        ))}
      </div>
    </nav>
  )
}
