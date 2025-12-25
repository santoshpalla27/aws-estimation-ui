import { useState, useEffect } from 'react';
import { getResults, ResultsResponse } from '../services/api';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import './Dashboard.css';

interface DashboardProps {
    jobId: string;
    onReset: () => void;
}

const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#fee140', '#30cfd0'];

function Dashboard({ jobId, onReset }: DashboardProps) {
    const [results, setResults] = useState<ResultsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchResults = async () => {
            try {
                const data = await getResults(jobId);
                setResults(data);
                setLoading(false);
            } catch (err: any) {
                setError(err.response?.data?.detail || err.message || 'Failed to fetch results');
                setLoading(false);
            }
        };

        fetchResults();
    }, [jobId]);

    if (loading) {
        return (
            <div className="dashboard-loading">
                <div className="spinner"></div>
                <p>Loading results...</p>
            </div>
        );
    }

    if (error || !results) {
        return (
            <div className="dashboard-error">
                <p>Error: {error || 'No results found'}</p>
                <button onClick={onReset} className="btn-primary">Upload New File</button>
            </div>
        );
    }

    // Prepare chart data
    const serviceData = Object.entries(results.breakdown_by_service).map(([name, value]) => ({
        name,
        value: Number(value.toFixed(2))
    }));

    const regionData = Object.entries(results.breakdown_by_region).map(([name, value]) => ({
        name,
        value: Number(value.toFixed(2))
    }));

    return (
        <div className="dashboard">
            <div className="dashboard-header">
                <h2>Cost Analysis Results</h2>
                <button onClick={onReset} className="btn-secondary">New Analysis</button>
            </div>

            {/* Summary Cards */}
            <div className="summary-cards">
                <div className="summary-card primary">
                    <div className="card-icon">💰</div>
                    <div className="card-content">
                        <h3>Total Monthly Cost</h3>
                        <p className="card-value">${results.total_monthly_cost.toFixed(2)}</p>
                    </div>
                </div>

                <div className="summary-card">
                    <div className="card-icon">📦</div>
                    <div className="card-content">
                        <h3>Total Resources</h3>
                        <p className="card-value">{results.total_resources}</p>
                    </div>
                </div>

                <div className="summary-card success">
                    <div className="card-icon">✅</div>
                    <div className="card-content">
                        <h3>Supported</h3>
                        <p className="card-value">{results.supported_resources}</p>
                    </div>
                </div>

                <div className="summary-card warning">
                    <div className="card-icon">⚠️</div>
                    <div className="card-content">
                        <h3>Unsupported</h3>
                        <p className="card-value">{results.unsupported_resources}</p>
                    </div>
                </div>
            </div>

            {/* Charts */}
            <div className="charts-grid">
                <div className="chart-card">
                    <h3>Cost by Service</h3>
                    {serviceData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={300}>
                            <PieChart>
                                <Pie
                                    data={serviceData}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                                    outerRadius={80}
                                    fill="#8884d8"
                                    dataKey="value"
                                >
                                    {serviceData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip formatter={(value: number) => `$${value.toFixed(2)}`} />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    ) : (
                        <p className="no-data">No service data available</p>
                    )}
                </div>

                <div className="chart-card">
                    <h3>Cost by Region</h3>
                    {regionData.length > 0 ? (
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={regionData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="name" />
                                <YAxis />
                                <Tooltip formatter={(value: number) => `$${value.toFixed(2)}`} />
                                <Bar dataKey="value" fill="#667eea" />
                            </BarChart>
                        </ResponsiveContainer>
                    ) : (
                        <p className="no-data">No region data available</p>
                    )}
                </div>
            </div>

            {/* Resource Table */}
            <div className="resources-section">
                <h3>Resource Details</h3>
                <div className="table-container">
                    <table className="resources-table">
                        <thead>
                            <tr>
                                <th>Resource Name</th>
                                <th>Type</th>
                                <th>Service</th>
                                <th>Region</th>
                                <th>Monthly Cost</th>
                            </tr>
                        </thead>
                        <tbody>
                            {results.resources.map((resource, index) => (
                                <tr key={index}>
                                    <td className="resource-name">{resource.name}</td>
                                    <td>{resource.type}</td>
                                    <td>{resource.service}</td>
                                    <td>{resource.region || 'N/A'}</td>
                                    <td className="cost">${resource.monthly_cost.toFixed(2)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Warnings and Errors */}
            {(results.warnings.length > 0 || results.errors.length > 0) && (
                <div className="alerts-section">
                    {results.warnings.length > 0 && (
                        <div className="alert warning">
                            <h4>⚠️ Warnings</h4>
                            <ul>
                                {results.warnings.map((warning, index) => (
                                    <li key={index}>{warning}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {results.errors.length > 0 && (
                        <div className="alert error">
                            <h4>❌ Errors</h4>
                            <ul>
                                {results.errors.map((error, index) => (
                                    <li key={index}>
                                        <strong>{error.resource}</strong> ({error.type}): {error.error}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default Dashboard;
