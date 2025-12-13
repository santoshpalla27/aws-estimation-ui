import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { ProjectWorkspace } from './pages/ProjectWorkspace'

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Layout />}>
                    <Route index element={<Dashboard />} />
                    <Route path="projects/:projectId" element={<ProjectWorkspace />} />
                </Route>
            </Routes>
        </BrowserRouter>
    )
}

export default App
