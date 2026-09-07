import React, { useState, useEffect, useRef } from 'react';
import { Upload, FileText, Trash2, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

const apiFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const token = localStorage.getItem('mrpl_token');
  const headers: Record<string, string> = { ...Object.fromEntries(Object.entries(options.headers || {})) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(url, { ...options, headers });
};

interface Document {
  document_id: string;
  document_name: string;
  chunks_indexed: number;
}

export const KnowledgeManager: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [uploadMessage, setUploadMessage] = useState<string>('');
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/api/knowledge/documents');
      if (res.ok) {
        const data = await res.json();
        setDocuments(Array.isArray(data) ? data : (data.documents || []));
      } else {
        throw new Error('Failed to fetch documents');
      }
    } catch (err) {
      console.error(err);
      setError('Could not load knowledge base documents.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = ['.pdf', '.docx', '.xlsx', '.csv', '.txt'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    if (!allowedTypes.includes(ext)) {
      setUploadStatus('error');
      setUploadMessage(`Unsupported file type: ${ext}. Please upload ${allowedTypes.join(', ')}.`);
      return;
    }

    await uploadFile(file);
    
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const uploadFile = async (file: File) => {
    setUploadStatus('uploading');
    setUploadMessage(`Uploading ${file.name}...`);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await apiFetch('/api/knowledge/ingest', {
        method: 'POST',
        body: formData,
        // Do not set Content-Type header, let the browser set it with boundary for FormData
      });

      if (res.ok) {
        setUploadStatus('success');
        setUploadMessage(`${file.name} successfully ingested.`);
        fetchDocuments();
      } else {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.message || 'Upload failed');
      }
    } catch (err: any) {
      console.error(err);
      setUploadStatus('error');
      setUploadMessage(err.message || 'An error occurred during upload.');
    }
  };

  const handleDelete = async (document_id: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    
    try {
      const res = await apiFetch(`/api/knowledge/documents/${document_id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchDocuments();
      } else {
        alert('Failed to delete document');
      }
    } catch (err) {
      console.error(err);
      alert('Error connecting to server.');
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Upload Section */}
      <section className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-[#1b4332] px-6 py-4">
          <h2 className="text-lg font-semibold text-white">Ingest New Document</h2>
        </div>
        <div className="p-8">
          <div 
            className="border-2 border-dashed border-slate-300 rounded-lg p-12 flex flex-col items-center justify-center text-center hover:bg-slate-50 hover:border-[#2d6a4f] transition-colors cursor-pointer"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="w-12 h-12 text-slate-400 mb-4" />
            <h3 className="text-lg font-medium text-slate-700">Drop files here or click to upload</h3>
            <p className="text-sm text-slate-500 mt-2">Supports PDF, DOCX, XLSX, CSV, TXT</p>
            <input 
              type="file" 
              ref={fileInputRef} 
              className="hidden" 
              accept=".pdf,.docx,.xlsx,.csv,.txt"
              onChange={handleFileSelect}
            />
          </div>

          {/* Upload Status */}
          {uploadStatus !== 'idle' && (
            <div className={`mt-6 p-4 rounded-md flex items-start ${
              uploadStatus === 'uploading' ? 'bg-blue-50 text-blue-700' :
              uploadStatus === 'success' ? 'bg-green-50 text-green-700' :
              'bg-red-50 text-red-700'
            }`}>
              {uploadStatus === 'uploading' && <Loader2 className="w-5 h-5 mr-3 animate-spin" />}
              {uploadStatus === 'success' && <CheckCircle className="w-5 h-5 mr-3" />}
              {uploadStatus === 'error' && <AlertCircle className="w-5 h-5 mr-3" />}
              <span className="font-medium">{uploadMessage}</span>
            </div>
          )}
        </div>
      </section>

      {/* Documents Table */}
      <section className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-[#1b4332] px-6 py-4 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-white">Knowledge Base Documents</h2>
          <span className="bg-[#2d6a4f] text-green-100 text-xs px-2.5 py-1 rounded-full font-medium">
            {documents.length} Items
          </span>
        </div>
        
        {loading ? (
          <div className="p-12 flex justify-center">
            <Loader2 className="w-8 h-8 text-[#1b4332] animate-spin" />
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">{error}</div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <FileText className="w-12 h-12 mx-auto text-slate-300 mb-4" />
            <p>No documents found. Upload one to get started.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 text-sm uppercase tracking-wider">
                  <th className="px-6 py-4 font-medium">Document Name</th>
                  <th className="px-6 py-4 font-medium">Chunks</th>
                  <th className="px-6 py-4 font-medium">Document ID</th>
                  <th className="px-6 py-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((doc) => (
                  <tr key={doc.document_id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4 flex items-center">
                      <FileText className="w-5 h-5 text-slate-400 mr-3" />
                      <span className="font-medium text-slate-800">{doc.document_name}</span>
                    </td>
                    <td className="px-6 py-4 text-slate-600">{doc.chunks_indexed}</td>
                    <td className="px-6 py-4 text-slate-500 text-sm font-mono">{doc.document_id}</td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={() => handleDelete(doc.document_id)}
                        className="text-slate-400 hover:text-red-500 transition-colors p-2 rounded-full hover:bg-red-50"
                        title="Delete Document"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};
