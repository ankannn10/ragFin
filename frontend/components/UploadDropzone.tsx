'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export default function UploadDropzone() {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (!acceptedFiles.length) return;
    setUploading(true);
    try {
      const file = acceptedFiles[0];
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/upload`, {
        method: 'POST',
        body: formData,
      });

      const json = await res.json();
      if (res.ok) setMessage(`Upload started • Task ID: ${json.task_id}`);
      else setMessage(json.detail || 'Upload failed');
    } catch (e: any) {
      setMessage('Upload error: ' + e?.message);
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
  });

  return (
    <div
      {...getRootProps({
        className: cn(
          'flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-6 transition-colors cursor-pointer',
          isDragActive ? 'bg-accent' : 'bg-card'
        ),
      })}
    >
      <input {...getInputProps()} />
      <p className="text-sm text-muted-foreground">
        {isDragActive ? 'Drop the 10-K PDF here…' : 'Drag & drop a 10-K PDF, or click to select'}
      </p>
      {uploading && <p className="text-xs mt-2">Uploading…</p>}
      {message && <p className="text-xs mt-2">{message}</p>}
      {!uploading && (
        <Button variant="secondary" size="sm" className="mt-4">
          Select file
        </Button>
      )}
    </div>
  );
} 