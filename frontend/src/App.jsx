import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import Navbar from './components/Navbar'
import AboutData from './pages/AboutData'
import HighestGaps from './pages/HighestGaps'
import NoData from './pages/NoData'
import Profile from './pages/Profile'
import Results from './pages/Results'

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-8 sm:py-12">
        <Routes>
          <Route path="/" element={<Profile />} />
          <Route path="/results" element={<Results />} />
          <Route path="/no-data" element={<NoData />} />
          <Route path="/gaps" element={<HighestGaps />} />
          <Route path="/about" element={<AboutData />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}
