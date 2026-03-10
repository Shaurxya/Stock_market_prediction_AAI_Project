import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import Home from './pages/Home'
import Predictions from './pages/Predictions'
import About from './pages/About'

export default function App() {
    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            minHeight: '100vh',
            background: '#0B0F19',
            color: '#f1f5f9',
            fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        }}>
            <Navbar />
            <main style={{
                flex: 1,
                width: '100%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                paddingTop: '64px',
            }}>
                <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/predict" element={<Predictions />} />
                    <Route path="/about" element={<About />} />
                </Routes>
            </main>
            <Footer />
        </div>
    )
}
