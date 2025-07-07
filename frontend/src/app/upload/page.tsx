'use client';

import { useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Sidebar from '@/components/ui/Sidebar';
import { 
  Upload, 
  FileText, 
  CheckCircle, 
  AlertCircle, 
  X,
  Cloud,
  Shield,
  Zap
} from 'lucide-react';

export default function UploadPage() {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    const pdfFiles = files.filter(file => file.type === 'application/pdf');
    
    if (pdfFiles.length > 0) {
      setUploadedFiles(prev => [...prev, ...pdfFiles]);
    }
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const pdfFiles = files.filter(file => file.type === 'application/pdf');
    setUploadedFiles(prev => [...prev, ...pdfFiles]);
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const uploadFiles = async () => {
    if (uploadedFiles.length === 0) return;

    setUploading(true);
    const newProgress: { [key: string]: number } = {};
    
    // Initialize progress for each file
    uploadedFiles.forEach(file => {
      newProgress[file.name] = 0;
    });
    setUploadProgress(newProgress);

    try {
      for (const file of uploadedFiles) {
        const formData = new FormData();
        formData.append('file', file);

        // Simulate upload progress
        for (let i = 0; i <= 100; i += 10) {
          await new Promise(resolve => setTimeout(resolve, 100));
          setUploadProgress(prev => ({
            ...prev,
            [file.name]: i
          }));
        }

        const response = await fetch('http://localhost:8000/upload/', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`Upload failed for ${file.name}`);
        }
      }

      // Clear files after successful upload
      setUploadedFiles([]);
      setUploadProgress({});
    } catch (error) {
      console.error('Upload error:', error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="border-b border-border bg-card/50 backdrop-blur-sm">
          <div className="flex items-center justify-between p-6">
            <div>
              <h1 className="text-2xl font-bold text-foreground">Document Upload</h1>
              <p className="text-muted-foreground">Upload financial documents for AI analysis</p>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Upload Area */}
            <Card className={`transition-all duration-200 ${isDragOver ? 'border-primary bg-primary/5' : ''}`}>
              <CardContent className="p-8">
                <div
                  className={`border-2 border-dashed rounded-lg p-12 text-center transition-all duration-200 ${
                    isDragOver 
                      ? 'border-primary bg-primary/5' 
                      : 'border-border hover:border-primary/50'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <div className="space-y-4">
                    <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
                      <Upload className="w-8 h-8 text-primary" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold mb-2">Upload Financial Documents</h3>
                      <p className="text-muted-foreground mb-4">
                        Drag and drop PDF files here, or click to browse
                      </p>
                      <Button onClick={() => document.getElementById('file-input')?.click()}>
                        <FileText className="w-4 h-4 mr-2" />
                        Choose Files
                      </Button>
                    </div>
                    <input
                      id="file-input"
                      type="file"
                      multiple
                      accept=".pdf"
                      onChange={handleFileSelect}
                      className="hidden"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Features */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="card-hover">
                <CardContent className="p-6">
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                      <Shield className="w-5 h-5 text-blue-500" />
                    </div>
                    <h3 className="font-semibold">Secure Processing</h3>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Your documents are processed securely with enterprise-grade encryption and privacy protection.
                  </p>
                </CardContent>
              </Card>

              <Card className="card-hover">
                <CardContent className="p-6">
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="w-10 h-10 bg-green-500/10 rounded-lg flex items-center justify-center">
                      <Zap className="w-5 h-5 text-green-500" />
                    </div>
                    <h3 className="font-semibold">Fast Processing</h3>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Advanced AI processes your documents quickly, extracting key information and creating searchable chunks.
                  </p>
                </CardContent>
              </Card>

              <Card className="card-hover">
                <CardContent className="p-6">
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center">
                      <Cloud className="w-5 h-5 text-purple-500" />
                    </div>
                    <h3 className="font-semibold">Cloud Storage</h3>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Documents are stored securely in the cloud with automatic backups and version control.
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* File List */}
            {uploadedFiles.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <FileText className="w-5 h-5" />
                    <span>Selected Files ({uploadedFiles.length})</span>
                  </CardTitle>
                  <CardDescription>
                    Files ready for upload and processing
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {uploadedFiles.map((file, index) => (
                      <div key={index} className="flex items-center justify-between p-3 rounded-lg border border-border">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 bg-blue-500/10 rounded-lg flex items-center justify-center">
                            <FileText className="w-4 h-4 text-blue-500" />
                          </div>
                          <div>
                            <p className="font-medium text-sm">{file.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {(file.size / 1024 / 1024).toFixed(2)} MB
                            </p>
                          </div>
                        </div>
                        
                        <div className="flex items-center space-x-3">
                          {uploadProgress[file.name] !== undefined && (
                            <div className="flex items-center space-x-2">
                              <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
                                <div 
                                  className="h-full bg-primary transition-all duration-300"
                                  style={{ width: `${uploadProgress[file.name]}%` }}
                                />
                              </div>
                              <span className="text-xs text-muted-foreground">
                                {uploadProgress[file.name]}%
                              </span>
                            </div>
                          )}
                          
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeFile(index)}
                            disabled={uploading}
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  <div className="flex justify-end space-x-3 mt-6">
                    <Button
                      variant="outline"
                      onClick={() => setUploadedFiles([])}
                      disabled={uploading}
                    >
                      Clear All
                    </Button>
                    <Button
                      onClick={uploadFiles}
                      disabled={uploading || uploadedFiles.length === 0}
                      className="min-w-[120px]"
                    >
                      {uploading ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                          Uploading...
                        </>
                      ) : (
                        <>
                          <Upload className="w-4 h-4 mr-2" />
                          Upload Files
                        </>
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Upload Guidelines */}
            <Card>
              <CardHeader>
                <CardTitle>Upload Guidelines</CardTitle>
                <CardDescription>
                  Best practices for optimal document processing
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-3">
                    <h4 className="font-semibold text-sm">Supported Formats</h4>
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      <li className="flex items-center space-x-2">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        <span>PDF documents</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        <span>SEC filings (10-K, 10-Q, etc.)</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        <span>Financial reports</span>
                      </li>
                    </ul>
                  </div>
                  
                  <div className="space-y-3">
                    <h4 className="font-semibold text-sm">Requirements</h4>
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      <li className="flex items-center space-x-2">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        <span>Maximum file size: 50MB</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        <span>Text-based PDFs (not scanned images)</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <CheckCircle className="w-4 h-4 text-green-500" />
                        <span>English language documents</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </main>
      </div>
    </div>
  );
}
