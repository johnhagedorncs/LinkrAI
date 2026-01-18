/**
 * API client for healthcare agent demo backend
 */

// Use environment variable for backend URL, fallback to localhost
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface TranscriptResponse {
  transcript: string;
  s3_uri: string;
  speakers: number;
}

export interface ProcessResponse {
  success: boolean;
  transcript: string;
  actions_taken: string[];
  results: Record<string, any>;
}

export async function uploadAndTranscribe(audioBlob: Blob): Promise<TranscriptResponse> {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.webm');

  const response = await fetch(`${API_BASE_URL}/api/upload-and-transcribe`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Transcription failed: ${response.statusText}`);
  }

  return response.json();
}

export async function processTranscript(transcript: string): Promise<ProcessResponse> {
  const response = await fetch(`${API_BASE_URL}/api/process`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ transcript }),
  });

  if (!response.ok) {
    throw new Error(`Processing failed: ${response.statusText}`);
  }

  return response.json();
}
