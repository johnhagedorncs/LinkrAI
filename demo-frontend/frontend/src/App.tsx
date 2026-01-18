import { useState, useRef } from 'react';
import { uploadAndTranscribe, processTranscript, ProcessResponse } from './api';
import './App.css';

type Step = 'idle' | 'recording' | 'uploading' | 'transcribing' | 'processing' | 'complete';

function App() {
  const [step, setStep] = useState<Step>('idle');
  const [transcript, setTranscript] = useState<string>('');
  const [results, setResults] = useState<ProcessResponse | null>(null);
  const [error, setError] = useState<string>('');

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
        await handleRecordingComplete(audioBlob);

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setStep('recording');
      setError('');
    } catch (err) {
      setError('Failed to access microphone. Please grant permission.');
      console.error('Error accessing microphone:', err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  };

  const handleRecordingComplete = async (audioBlob: Blob) => {
    try {
      // Step 1: Upload and transcribe
      setStep('uploading');
      const transcriptResponse = await uploadAndTranscribe(audioBlob);

      setStep('transcribing');
      setTranscript(transcriptResponse.transcript);

      // Step 2: Process transcript through agents
      setStep('processing');
      const processResponse = await processTranscript(transcriptResponse.transcript);

      setResults(processResponse);
      setStep('complete');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setStep('idle');
      console.error('Error processing recording:', err);
    }
  };

  const reset = () => {
    setStep('idle');
    setTranscript('');
    setResults(null);
    setError('');
    chunksRef.current = [];
  };

  const getStepMessage = () => {
    switch (step) {
      case 'recording':
        return 'Recording conversation...';
      case 'uploading':
        return 'Uploading audio to S3...';
      case 'transcribing':
        return 'Transcribing with AWS Transcribe Medical...';
      case 'processing':
        return 'Processing through agent system...';
      case 'complete':
        return 'Complete!';
      default:
        return '';
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>Artera Agent Demo</h1>
        <p>Record a doctor-patient conversation and watch the AI agents work</p>
      </header>

      <main className="main">
        {/* Recording Controls */}
        <div className="card">
          <h2>Step 1: Record Conversation</h2>
          {step === 'idle' && (
            <button onClick={startRecording} className="btn btn-primary">
              Start Recording
            </button>
          )}
          {step === 'recording' && (
            <button onClick={stopRecording} className="btn btn-danger">
              Stop Recording
            </button>
          )}
          {step !== 'idle' && step !== 'recording' && (
            <div className="progress">
              <div className="spinner"></div>
              <p>{getStepMessage()}</p>
            </div>
          )}
          {error && <div className="error">{error}</div>}
        </div>

        {/* Transcript Display */}
        {transcript && (
          <div className="card">
            <h2>Step 2: Transcript</h2>
            <div className="transcript">
              {transcript.split('\n').map((line, i) => {
                const [speaker, ...textParts] = line.split(':');
                const text = textParts.join(':');
                return (
                  <div key={i} className="transcript-line">
                    <strong>{speaker}:</strong>
                    <span>{text}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Results Display */}
        {results && (
          <div className="card">
            <h2>Step 3: Agent Actions</h2>
            <div className="actions">
              {results.actions_taken.map((action, i) => (
                <div key={i} className="action-item">
                  {action}
                </div>
              ))}
            </div>

            <h3>Results</h3>
            <div className="results">
              {Object.entries(results.results).map(([key, value]) => (
                <div key={key} className="result-item">
                  <strong>{key}:</strong>
                  <pre style={{ whiteSpace: 'pre-wrap' }}>
                    {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
                  </pre>
                </div>
              ))}
            </div>

            <button onClick={reset} className="btn btn-secondary">
              Start Over
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
