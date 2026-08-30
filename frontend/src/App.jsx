import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import BottomNav from './components/BottomNav'

import HomePage from './pages/HomePage'
import RecipeDetailPage from './pages/RecipeDetailPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ProfilePage from './pages/ProfilePage'
import HistoryPage from './pages/HistoryPage'
import BookmarksPage from './pages/BookmarksPage'
import HowItWorksPage from './pages/HowItWorksPage'
import EvaluationPage from './pages/EvaluationPage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        {/* pb-16 sm:pb-0: reserve space for the mobile bottom nav on small screens */}
        <div className="pb-16 sm:pb-0">
          <Routes>
            <Route path="/"              element={<HomePage />} />
            <Route path="/recipe/:id"    element={<RecipeDetailPage />} />
            <Route path="/login"         element={<LoginPage />} />
            <Route path="/register"      element={<RegisterPage />} />
            <Route path="/profile"       element={<ProfilePage />} />
            <Route path="/history"       element={<HistoryPage />} />
            <Route path="/bookmarks"     element={<BookmarksPage />} />
            <Route path="/how-it-works"  element={<HowItWorksPage />} />
            <Route path="/evaluation"    element={<EvaluationPage />} />
          </Routes>
        </div>
        <BottomNav />
      </BrowserRouter>
    </AuthProvider>
  )
}
