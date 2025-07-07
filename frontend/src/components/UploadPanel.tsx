'use client';
import { useState, useRef, useCallback } from 'react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { UploadCloud, File, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function UploadPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [msg, setMsg] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback((selectedFile: File | null) => {
    if (selectedFile && (selectedFile.type === 'application/pdf' || selectedFile.name.endsWith('.html'))) {
      setFile(selectedFile);
      setMsg('');
    } else {
      setMsg('Please select a valid PDF or HTML file.');
    }
  }, []);

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
    const droppedFile = e.dataTransfer.files[0];
    handleFileSelect(droppedFile);
  }, [handleFileSelect]);

  async function handleUpload() {
    if (!file) return;

    setIsUploading(true);
    setMsg('Uploading document...');

    try {
      const form = new FormData();
      form.append('file', file);

      const res = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: form,
      });

      if (res.ok) {
        setMsg('✅ Document uploaded successfully! Processing will begin shortly.');
        setFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      } else {
        setMsg('❌ Upload failed. Please try again.');
      }
    } catch (error) {
      console.error('Upload error:', error);
      setMsg('❌ Upload failed. Please check your connection and try again.');
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <Card>
      <CardContent className="p-6 space-y-6">
        <div
          className={cn(
            'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer',
            isDragOver ? 'border-primary/50 bg-primary/5' : 'border-border'
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.html"
            onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
            className="hidden"
          />
          <div className="space-y-2">
            <div className="mx-auto w-12 h-12 bg-muted rounded-full flex items-center justify-center">
              <UploadCloud className="w-6 h-6 text-muted-foreground" />
            </div>
            <p className="font-medium">
              {isDragOver ? 'Drop your file here' : 'Drag & drop or click to browse'}
            </p>
            <p className="text-xs text-muted-foreground">PDF or HTML up to 50MB</p>
          </div>
        </div>

        {file && (
          <div className="flex items-center justify-between rounded-md border p-3">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-primary/10 rounded flex items-center justify-center">
                <File className="w-4 h-4 text-primary" />
              </div>
              <div>
                <p className="text-sm font-medium">{file.name}</p>
                <p className="text-xs text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => {
                setFile(null);
                if (fileInputRef.current) fileInputRef.current.value = '';
              }}
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        )}

        <Button className="w-full" onClick={handleUpload} disabled={!file || isUploading}>
          {isUploading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Uploading...
            </>
          ) : (
            <>
              <UploadCloud className="w-4 h-4 mr-2" /> Upload Document
            </>
          )}
        </Button>

        {msg && <p className="text-sm text-center text-muted-foreground">{msg}</p>}
      </CardContent>
    </Card>
  );
}
