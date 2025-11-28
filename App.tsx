import React, { useState, useEffect } from 'react';
import ResourceForm from './components/ResourceForm';
import ResourceList from './components/ResourceList';
import CostDashboard from './components/CostDashboard';
import CredentialsModal from './components/CredentialsModal';
import { InfrastructureResource, CostEstimationResult } from './types';
import { estimateInfrastructureCost, AwsCredentials } from './services/awsPriceService';
import { Calculator, Cloud, Settings, Sparkles } from 'lucide-react';

function App() {
  const [resources, setResources] = useState<InfrastructureResource[]>([]);
  const [estimation, setEstimation] = useState<CostEstimationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [credentials, setCredentials] = useState<AwsCredentials | null>(null);
  const [isCredentialsModalOpen, setIsCredentialsModalOpen] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('aws_credentials');
    const envAccessKey = import.meta.env.VITE_AWS_ACCESS_KEY_ID;
    const envSecretKey = import.meta.env.VITE_AWS_SECRET_ACCESS_KEY;
    const envRegion = import.meta.env.VITE_AWS_REGION || 'us-east-1';

    if (envAccessKey && envSecretKey) {
      setCredentials({
        accessKeyId: envAccessKey,
        secretAccessKey: envSecretKey,
        region: envRegion
      });
    } else if (stored) {
      try {
        setCredentials(JSON.parse(stored));
      } catch (e) {
        console.error("Failed to parse stored credentials");
      }
    } else {
      setIsCredentialsModalOpen(true);
    }
  }, []);

  const handleSaveCredentials = (creds: AwsCredentials) => {
    setCredentials(creds);
    localStorage.setItem('aws_credentials', JSON.stringify(creds));
  };

  const handleAddResource = (resource: InfrastructureResource) => {
    setResources((prev) => [...prev, resource]);
    if (estimation) {
      // setEstimation(null); 
    }
  };

  const handleRemoveResource = (id: string) => {
    setResources((prev) => prev.filter((r) => r.id !== id));
  };

  const handleCalculate = async () => {
    if (resources.length === 0) return;

    if (!credentials) {
      setIsCredentialsModalOpen(true);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const result = await estimateInfrastructureCost(resources, credentials);
      setEstimation(result);
    } catch (err) {
      setError("Failed to generate cost estimation. Please check your credentials and try again.");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900">
      <CredentialsModal
        isOpen={isCredentialsModalOpen}
        onClose={() => setIsCredentialsModalOpen(false)}
        onSave={handleSaveCredentials}
        initialCredentials={credentials}
      />

      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm backdrop-blur-sm bg-white/90">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="bg-gradient-to-br from-indigo-600 to-violet-600 p-2 rounded-lg shadow-md">
              <Cloud className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold text-slate-800 tracking-tight block leading-none">CloudCast</span>
              <span className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">AWS Price List API</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsCredentialsModalOpen(true)}
              className="text-slate-500 hover:text-indigo-600 transition-colors p-2 rounded-full hover:bg-slate-100"
              title="AWS Credentials"
            >
              <Settings className="w-5 h-5" />
            </button>
            <div className="hidden md:flex items-center gap-1.5 text-xs text-indigo-700 font-medium px-3 py-1 bg-indigo-50 rounded-full border border-indigo-100">
              <Sparkles className="w-3 h-3" />
              Real-time Pricing
            </div>
          </div>
        </div>
      </header>

      <main className="flex-grow container mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-32">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">

          {/* Left Column: Builder */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            <div>
              <div className="mb-6">
                <h1 className="text-2xl font-bold text-slate-900 mb-2">Infrastructure Designer</h1>
                <p className="text-slate-500 text-sm max-w-2xl">
                  Construct your AWS stack below. We query the official AWS Price List API for accurate estimates.
                </p>
              </div>
              <ResourceForm onAddResource={handleAddResource} />
            </div>

            <ResourceList
              resources={resources}
              onRemoveResource={handleRemoveResource}
            />

            {resources.length > 0 && (
              <div className="sticky bottom-6 z-30 pt-4">
                <div className="absolute inset-0 -z-10 bg-gradient-to-t from-slate-50 via-slate-50 to-transparent -top-12"></div>
                <div className="bg-white/80 backdrop-blur-md p-1.5 rounded-2xl border border-slate-200 shadow-xl flex gap-2">
                  <button
                    onClick={handleCalculate}
                    disabled={isLoading}
                    className="flex-1 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-400 text-white font-semibold py-3.5 px-6 rounded-xl shadow-sm transform transition-all active:scale-[0.99] flex items-center justify-center gap-3 text-base"
                  >
                    {isLoading ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Fetching Prices...</span>
                      </>
                    ) : (
                      <>
                        <Calculator className="w-5 h-5" /> Generate Estimate
                      </>
                    )}
                  </button>
                </div>
                {error && (
                  <div className="mt-3 p-3 bg-red-50 text-red-700 text-sm rounded-lg border border-red-200 animate-fadeIn">
                    {error}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Column: Results */}
          <div className="lg:col-span-5 relative">
            <div className="sticky top-24 transition-all duration-300">
              <CostDashboard estimation={estimation} isLoading={isLoading} />
            </div>
          </div>
        </div>
      </main>

      <footer className="bg-white border-t border-slate-200 py-8 mt-auto">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-slate-400 text-sm">© {new Date().getFullYear()} CloudCast Estimator. Built with AWS Price List API & React.</p>
        </div>
      </footer>
    </div>
  );
}

export default App;