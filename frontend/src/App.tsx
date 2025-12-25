import { useState } from 'react';
import Upload from './components/Upload';
import Dashboard from './components/Dashboard';
import './App.css';

function App() {
    const [jobId, setJobId] = useState<string | null>(null);
    const [showDashboard, setShowDashboard] = useState(false);

    const handleUploadSuccess = (newJobId: string) => {
        setJobId(newJobId);
        setShowDashboard(true);
    };

    const handleReset = () => {
        setJobId(null);
        setShowDashboard(false);
    };

    return (
        <div className="app">
            <header className="app-header">
                <h1>AWS Terraform Cost Calculator</h1>
                <p>Calculate AWS costs from your Terraform files</p>
            </header>

            <main className="app-main">
                {!showDashboard ? (
                    <Upload onUploadSuccess={handleUploadSuccess} />
                ) : (
                    <Dashboard jobId={jobId!} onReset={handleReset} />
                )}
            </main>

            <footer className="app-footer">
                <p>Production-ready AWS cost estimation from Terraform</p>
            </footer>
        </div>
    );
}

export default App;
