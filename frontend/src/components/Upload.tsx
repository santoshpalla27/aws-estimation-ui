import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadFile, analyzeJob } from '../services/api';
import './Upload.css';

interface UploadProps {
    onUploadSuccess: (jobId: string) => void;
}

function Upload({ onUploadSuccess }: UploadProps) {
    const [uploading, setUploading] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const onDrop = useCallback(async (acceptedFiles: File[]) => {
        if (acceptedFiles.length === 0) return;

        const file = acceptedFiles[0];
        setError(null);
        setUploading(true);

        try {
            // Upload file
            const uploadResponse = await uploadFile(file);
            console.log('Upload response:', uploadResponse);

            setUploading(false);
            setAnalyzing(true);

            // Start analysis
            const analysisResponse = await analyzeJob(uploadResponse.job_id);
            console.log('Analysis response:', analysisResponse);

            setAnalyzing(false);
            onUploadSuccess(uploadResponse.job_id);
        } catch (err: any) {
            setUploading(false);
            setAnalyzing(false);
            setError(err.response?.data?.detail || err.message || 'Upload failed');
            console.error('Upload error:', err);
        }
    }, [onUploadSuccess]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'text/plain': ['.tf'],
            'application/zip': ['.zip'],
        },
        multiple: false,
        maxSize: 50 * 1024 * 1024, // 50MB
    });

    return (
        <div className="upload-container">
            <div className="upload-card">
                <h2>Upload Terraform Files</h2>
                <p className="upload-description">
                    Upload a single .tf file or a .zip containing your Terraform configuration
                </p>

                <div
                    {...getRootProps()}
                    className={`dropzone ${isDragActive ? 'active' : ''} ${uploading || analyzing ? 'disabled' : ''}`}
                >
                    <input {...getInputProps()} disabled={uploading || analyzing} />

                    {uploading ? (
                        <div className="upload-status">
                            <div className="spinner"></div>
                            <p>Uploading file...</p>
                        </div>
                    ) : analyzing ? (
                        <div className="upload-status">
                            <div className="spinner"></div>
                            <p>Analyzing Terraform and calculating costs...</p>
                            <p className="upload-note">This may take a few moments</p>
                        </div>
                    ) : isDragActive ? (
                        <p className="dropzone-text">Drop the file here...</p>
                    ) : (
                        <>
                            <svg className="upload-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                            <p className="dropzone-text">
                                Drag & drop a Terraform file or .zip here, or click to select
                            </p>
                            <p className="dropzone-hint">
                                Supports .tf files and .zip archives (max 50MB)
                            </p>
                        </>
                    )}
                </div>

                {error && (
                    <div className="error-message">
                        <svg className="error-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <p>{error}</p>
                    </div>
                )}

                <div className="upload-features">
                    <div className="feature">
                        <svg className="feature-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>Real AWS pricing data</span>
                    </div>
                    <div className="feature">
                        <svg className="feature-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        <span>Instant cost calculation</span>
                    </div>
                    <div className="feature">
                        <svg className="feature-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                        <span>Detailed breakdowns</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Upload;
