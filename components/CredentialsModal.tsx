import React, { useState, useEffect } from 'react';
import { Key, Save, X, Eye, EyeOff } from 'lucide-react';
import { AwsCredentials } from '../services/awsPriceService';

interface CredentialsModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (creds: AwsCredentials) => void;
    initialCredentials?: AwsCredentials | null;
}

const CredentialsModal: React.FC<CredentialsModalProps> = ({ isOpen, onClose, onSave, initialCredentials }) => {
    const [accessKeyId, setAccessKeyId] = useState('');
    const [secretAccessKey, setSecretAccessKey] = useState('');
    const [showSecret, setShowSecret] = useState(false);

    useEffect(() => {
        if (initialCredentials) {
            setAccessKeyId(initialCredentials.accessKeyId);
            setSecretAccessKey(initialCredentials.secretAccessKey);
        }
    }, [initialCredentials]);

    if (!isOpen) return null;

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSave({ accessKeyId, secretAccessKey, region: 'us-east-1' }); // Default region for pricing API
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
                <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                    <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                        <Key className="w-5 h-5 text-indigo-600" />
                        AWS Credentials
                    </h2>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    <div className="p-3 bg-blue-50 text-blue-700 text-xs rounded-lg border border-blue-100">
                        <strong>Note:</strong> Your credentials are stored locally in your browser and used only to query the AWS Price List API. They are never sent to any other server.
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Access Key ID</label>
                        <input
                            type="text"
                            required
                            value={accessKeyId}
                            onChange={(e) => setAccessKeyId(e.target.value)}
                            className="w-full rounded-lg border-slate-300 border px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                            placeholder="AKIA..."
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Secret Access Key</label>
                        <div className="relative">
                            <input
                                type={showSecret ? "text" : "password"}
                                required
                                value={secretAccessKey}
                                onChange={(e) => setSecretAccessKey(e.target.value)}
                                className="w-full rounded-lg border-slate-300 border px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all pr-10"
                                placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
                            />
                            <button
                                type="button"
                                onClick={() => setShowSecret(!showSecret)}
                                className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                            >
                                {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                        </div>
                    </div>

                    <div className="pt-2 flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm flex items-center gap-2 transition-colors"
                        >
                            <Save className="w-4 h-4" />
                            Save Credentials
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default CredentialsModal;
