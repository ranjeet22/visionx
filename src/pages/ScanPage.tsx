import React, { useState, useEffect, useRef } from 'react';
import {
  ScanLine,
  ArrowLeft,
  Sparkles,
  X,
  Send,
  Mic,
  Square,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { useRouter } from '../lib/useRouter';
import { useCamera } from '../hooks/useCamera';
import { YoloDetectionService } from '../features/detection/detection.service';
import { StrandsAgentService } from '../features/assistant/assistant.service';
import { TranscriptionService } from '../features/assistant/transcription.service';
import { getTimestamp, generateId } from '../lib/utils';
import type { ScannerInputMode, DetectedWasteObject, AssistantResponse } from '../types';
import { Badge } from '../components/ui/Badge';
import { InputModeSelector } from '../components/vision/InputModeSelector';
import { CameraViewfinder } from '../components/vision/CameraViewfinder';
import { ImageUploadPanel } from '../components/vision/ImageUploadPanel';
import { CapturedPreviewCard } from '../components/vision/CapturedPreviewCard';
import { AnalysisResultPanel } from '../components/vision/AnalysisResultPanel';
import './ScanPage.css';

export const ScanPage: React.FC = () => {
  const { navigate } = useRouter();

  // Input Mode: 'camera' | 'upload'
  const [inputMode, setInputMode] = useState<ScannerInputMode>('camera');

  // Selected Image state (Blob + object URL)
  const [selectedImage, setSelectedImage] = useState<{
    blob: Blob;
    url: string;
    sourceMode: ScannerInputMode;
  } | null>(null);

  // Real Detection State (Dual-Model Pipeline)
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [hasAnalyzed, setHasAnalyzed] = useState<boolean>(false);
  const [detections, setDetections] = useState<DetectedWasteObject[]>([]);
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Backend Health Status
  const [backendHealth, setBackendHealth] = useState<{
    isOnline: boolean;
    device?: string;
    classesCount?: number;
  }>({ isOnline: false });

  // Assistant Drawer State (Powered by Strands Agents)
  const [isAssistantOpen, setIsAssistantOpen] = useState<boolean>(false);
  const [assistantInput, setAssistantInput] = useState<string>('');
  const [assistantLoading, setAssistantLoading] = useState<boolean>(false);
  const [chatHistory, setChatHistory] = useState<{
    id: string;
    sender: 'user' | 'assistant';
    text: string;
    sources?: string[];
    needsVerification?: boolean;
    suggestedQuestions?: string[];
    uncertaintyNote?: string | null;
    timestamp: string;
  }[]>([]);

  // Voice Recording state (Powered by Cactus Compute Whistle)
  const [isRecordingVoice, setIsRecordingVoice] = useState<boolean>(false);
  const [isTranscribingVoice, setIsTranscribingVoice] = useState<boolean>(false);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioStreamRef = useRef<MediaStream | null>(null);

  // Camera Hook
  const {
    videoRef,
    isActive: isCameraActive,
    isRequesting: isCameraRequesting,
    error: cameraError,
    facingMode,
    stream,
    startCamera,
    stopCamera,
    toggleFacingMode,
    captureFrame,
  } = useCamera();

  // Check Backend Health on Mount
  useEffect(() => {
    let isMounted = true;
    const checkStatus = async () => {
      const health = await YoloDetectionService.checkHealth();
      if (isMounted) {
        setBackendHealth(health);
      }
    };
    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Cleanup audio tracks and object URLs on unmount
  useEffect(() => {
    return () => {
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Helper to safely revoke object URL and clean previous image
  const clearSelectedImage = () => {
    if (selectedImage?.url) {
      try {
        URL.revokeObjectURL(selectedImage.url);
      } catch {
        // ignore
      }
    }
    setSelectedImage(null);
  };

  // Switch input mode (Camera vs Upload)
  const handleModeChange = (mode: ScannerInputMode) => {
    if (mode === inputMode) return;

    if (inputMode === 'camera' && isCameraActive) {
      stopCamera();
    }

    clearSelectedImage();
    resetDetectionState();
    setInputMode(mode);
  };

  const resetDetectionState = () => {
    setDetections([]);
    setSelectedObjectId(null);
    setHasAnalyzed(false);
    setErrorMessage(null);
  };

  // Handle frame capture from live camera
  const handleCaptureFrame = async (liveDets?: DetectedWasteObject[]) => {
    const captured = await captureFrame();
    if (captured) {
      clearSelectedImage();
      setSelectedImage({
        blob: captured.blob,
        url: captured.url,
        sourceMode: 'camera',
      });
      if (liveDets && liveDets.length > 0) {
        setDetections(liveDets);
        setSelectedObjectId(liveDets[0].id);
        setHasAnalyzed(true);
        setErrorMessage(null);
      } else {
        resetDetectionState();
      }
    }
  };

  // Handle image selected via file upload
  const handleImageUploaded = (blob: Blob, url: string) => {
    clearSelectedImage();
    setSelectedImage({
      blob,
      url,
      sourceMode: 'upload',
    });
    resetDetectionState();
  };

  // Retake or pick a different image
  const handleRetry = () => {
    clearSelectedImage();
    resetDetectionState();
    if (inputMode === 'camera' && !isCameraActive) {
      startCamera();
    }
  };

  // Main Detection Trigger: Invokes backend dual-model vision pipeline
  const handleAnalyzeWaste = async () => {
    if (!selectedImage) return;

    setIsAnalyzing(true);
    setErrorMessage(null);

    try {
      const res = await YoloDetectionService.detectObjects(selectedImage.blob, 0.18);

      if (res.success && res.detections) {
        setDetections(res.detections);
        setHasAnalyzed(true);
        if (res.detections.length > 0) {
          setSelectedObjectId(res.detections[0].id);
        } else {
          setSelectedObjectId(null);
        }

        if (res.error) {
          // Informative notice for partial model failures (e.g. Roboflow key missing)
          setErrorMessage(res.error);
        }
      } else {
        setErrorMessage(res.error || 'Dual-model inference failed. Please verify backend service.');
        setDetections([]);
        setHasAnalyzed(true);
      }
    } catch (err: any) {
      setErrorMessage(`Failed to connect to VisionX server: ${err.message || err}`);
      setDetections([]);
      setHasAnalyzed(true);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Reset entire analysis to scan a new item
  const handleResetAnalysis = () => {
    clearSelectedImage();
    resetDetectionState();
    setChatHistory([]);
  };

  // Select an individual detected object from chips or bounding boxes
  const handleSelectObject = (id: string) => {
    setSelectedObjectId(id);
  };

  // Currently selected object
  const selectedObject: DetectedWasteObject | null =
    detections.find((d) => d.id === selectedObjectId) || (detections.length > 0 ? detections[0] : null);

  const currentIndex = detections.findIndex((d) => d.id === selectedObject?.id);

  const handleSelectNext = () => {
    if (currentIndex >= 0 && currentIndex < detections.length - 1) {
      setSelectedObjectId(detections[currentIndex + 1].id);
    }
  };

  const handleSelectPrev = () => {
    if (currentIndex > 0) {
      setSelectedObjectId(detections[currentIndex - 1].id);
    }
  };

  const isSelectedPerson =
    selectedObject?.model_source === 'ultralytics_person' ||
    selectedObject?.model_class_name === 'person' ||
    selectedObject?.waste_category === 'non_waste' ||
    selectedObject?.waste_category === null;

  // Grounded context for starter chips
  const starterQuestions = selectedObject
    ? isSelectedPerson
      ? [
          'Why was a person detected in this photo?',
          'Are there any recyclable waste items in this frame?',
          'How does the dual-model vision pipeline work?',
        ]
      : [
          `How should I dispose of this ${selectedObject.display_name}?`,
          `What preparation steps are required before recycling?`,
          `What are the contamination hazards for this material?`,
        ]
    : [
        'How do I properly sort mixed recyclable containers?',
        'What items cause mechanical sorting failures?',
        'What are the most common household recycling errors?',
      ];

  // Send message to Strands conversational agent
  const handleAskAssistant = async (questionText: string) => {
    if (!questionText.trim()) return;
    const userMsgTime = getTimestamp();

    setChatHistory((prev) => [
      ...prev,
      {
        id: generateId('user'),
        sender: 'user',
        text: questionText,
        timestamp: userMsgTime,
      },
    ]);
    setAssistantInput('');
    setAssistantLoading(true);

    try {
      const response: AssistantResponse = await StrandsAgentService.ask({
        question: questionText,
        selectedObject,
        allDetections: detections,
        history: chatHistory.map((m) => ({ sender: m.sender, text: m.text })),
        sessionId: 'visionx-session-' + (selectedObject?.id || 'live-frame'),
      });

      setChatHistory((prev) => [
        ...prev,
        {
          id: generateId('assistant'),
          sender: 'assistant',
          text: response.message,
          sources: response.sourceUrls,
          needsVerification: response.needsVerification,
          suggestedQuestions: response.suggestedQuestions,
          uncertaintyNote: response.uncertaintyNote,
          timestamp: response.timestamp || userMsgTime,
        },
      ]);
    } catch {
      setChatHistory((prev) => [
        ...prev,
        {
          id: generateId('err'),
          sender: 'assistant',
          text: 'VisionX Strands Agent encountered a connection issue. Please verify that the backend server is running.',
          timestamp: userMsgTime,
        },
      ]);
    } finally {
      setAssistantLoading(false);
    }
  };

  // Voice recording handlers (Whistle STT integration)
  const startVoiceRecording = async () => {
    setVoiceError(null);
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setVoiceError('Audio recording is not supported in this browser.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;
      audioChunksRef.current = [];

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')
        ? 'audio/ogg;codecs=opus'
        : '';

      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        // Stop audio tracks immediately to release the microphone hardware
        if (audioStreamRef.current) {
          audioStreamRef.current.getTracks().forEach((track) => track.stop());
          audioStreamRef.current = null;
        }

        const audioBlob = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || 'audio/webm',
        });

        if (audioBlob.size < 100) {
          setVoiceError('Audio recording was too short or empty.');
          setIsTranscribingVoice(false);
          return;
        }

        setIsTranscribingVoice(true);
        try {
          const res = await TranscriptionService.transcribe(audioBlob);
          if (res.success && res.text) {
            // Inserts transcript into text field for user review and editing before sending!
            setAssistantInput((prev) => (prev ? `${prev} ${res.text}` : res.text));
          } else {
            setVoiceError(res.error || 'No speech recognized. Please try again.');
          }
        } catch (err: any) {
          setVoiceError(`Transcription error: ${err.message || err}`);
        } finally {
          setIsTranscribingVoice(false);
        }
      };

      recorder.start(250);
      setIsRecordingVoice(true);
    } catch (err: any) {
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setVoiceError('Microphone permission was denied. Please allow microphone access in your browser.');
      } else {
        setVoiceError(`Could not access microphone: ${err.message || err}`);
      }
      setIsRecordingVoice(false);
    }
  };

  const stopVoiceRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsRecordingVoice(false);
  };

  // Cleanup object URLs on unmount
  useEffect(() => {
    return () => {
      if (selectedImage?.url) {
        try {
          URL.revokeObjectURL(selectedImage.url);
        } catch {
          // ignore
        }
      }
    };
  }, [selectedImage]);

  return (
    <div className="scan-page-root">
      {/* Top Scanner Navigation Bar */}
      <header className="scan-header-bar">
        <div className="page-container scan-nav-inner">
          <div className="scan-nav-left">
            <button
              type="button"
              className="back-home-btn"
              onClick={() => {
                if (isCameraActive) stopCamera();
                navigate('/');
              }}
              aria-label="Back to VisionX Home"
            >
              <ArrowLeft size={16} strokeWidth={2.5} />
              <span>Back to Home</span>
            </button>

            <div className="scan-brand-badge">
              <span className="scan-logo-box">
                <ScanLine size={16} strokeWidth={2.5} />
              </span>
              <span className="scan-brand-title">
                Vision<span className="scan-brand-x">X</span>
              </span>
              <span className="scan-status-tag">DUAL-VISION</span>
            </div>
          </div>

          <div className="scan-nav-right">
            {backendHealth.isOnline ? (
              <Badge variant="live" size="sm">
                DUAL-MODEL VISION LIVE ({backendHealth.device?.toUpperCase() || 'CPU'})
              </Badge>
            ) : (
              <Badge variant="sun" size="sm">
                LOCAL SERVER READY (START WITH PYTHON)
              </Badge>
            )}
          </div>
        </div>
      </header>

      {/* Main Workspace Container */}
      <main className="scan-workspace-main">
        <div className="page-container">
          {/* Page Heading */}
          <div className="scan-page-heading">
            <div className="scan-eyebrow-row">
              <span className="scan-eyebrow-pill">VISIONX / DUAL-MODEL PIPELINE</span>
            </div>
            <h1 className="scan-page-title">
              Dual-Model <mark className="highlighter">Vision Pipeline</mark>.
            </h1>
            <p className="scan-page-subtitle">
              Combining Ultralytics Person Detection and Roboflow Pretrained Waste Detection. Inspect multi-object bounding boxes, identify non-waste people, and voice questions to our AI assistant.
            </p>
          </div>

          {/* Two-Column Responsive Workspace Grid */}
          <div className="scan-workspace-grid">
            {/* LEFT COLUMN: Input Workspace */}
            <div className="workspace-column-input">
              <InputModeSelector
                mode={inputMode}
                onModeChange={handleModeChange}
                disabled={isAnalyzing}
              />

              {/* View 1: When no image is captured yet */}
              {!selectedImage && (
                <>
                  {inputMode === 'camera' ? (
                    <CameraViewfinder
                      videoRef={videoRef}
                      stream={stream}
                      isActive={isCameraActive}
                      isRequesting={isCameraRequesting}
                      facingMode={facingMode}
                      error={cameraError}
                      onStartCamera={startCamera}
                      onStopCamera={stopCamera}
                      onToggleFacingMode={toggleFacingMode}
                      onCaptureFrame={handleCaptureFrame}
                    />
                  ) : (
                    <ImageUploadPanel
                      onImageSelected={handleImageUploaded}
                      disabled={isAnalyzing}
                    />
                  )}
                </>
              )}

              {/* View 2: When an image is captured or uploaded */}
              {selectedImage && (
                <CapturedPreviewCard
                  imageUrl={selectedImage.url}
                  sourceMode={selectedImage.sourceMode}
                  detections={detections}
                  selectedObjectId={selectedObjectId}
                  onSelectObject={handleSelectObject}
                  onAnalyze={handleAnalyzeWaste}
                  onRetry={handleRetry}
                  isAnalyzing={isAnalyzing}
                  hasAnalyzed={hasAnalyzed}
                  errorMessage={errorMessage}
                />
              )}
            </div>

            {/* RIGHT COLUMN: Analysis & Guidance Results */}
            <div className="workspace-column-result">
              <AnalysisResultPanel
                selectedObject={selectedObject}
                totalDetections={detections.length}
                currentIndex={currentIndex}
                isAnalyzing={isAnalyzing}
                hasAnalyzed={hasAnalyzed}
                onSelectNext={handleSelectNext}
                onSelectPrev={handleSelectPrev}
                onReset={handleResetAnalysis}
                onOpenAssistant={() => setIsAssistantOpen(true)}
              />
            </div>
          </div>
        </div>
      </main>

      {/* Assistant Modal / Drawer */}
      {isAssistantOpen && (
        <div className="assistant-modal-backdrop" role="dialog" aria-modal="true">
          <div className="assistant-drawer-card">
            <div className="drawer-header">
              <div className="drawer-title-group">
                <span className="drawer-icon-box">
                  <Sparkles size={18} strokeWidth={2.5} />
                </span>
                <div>
                  <h4 className="drawer-title">VisionX Conversational Assistant</h4>
                  <span className="drawer-subtitle">
                    Grounded with {selectedObject ? selectedObject.display_name : 'Municipal Waste'} context
                  </span>
                </div>
              </div>
              <button
                type="button"
                className="drawer-close-btn"
                onClick={() => setIsAssistantOpen(false)}
                aria-label="Close assistant"
              >
                <X size={18} strokeWidth={2.5} />
              </button>
            </div>

            <div className="drawer-chat-body">
              {chatHistory.length === 0 ? (
                <div className="drawer-empty-state">
                  <p className="empty-prompt-title">Suggested questions for this item:</p>
                  <div className="suggested-questions-list">
                    {starterQuestions.map((q, idx) => (
                      <button
                        key={idx}
                        type="button"
                        className="suggested-q-btn"
                        onClick={() => handleAskAssistant(q)}
                      >
                        <span>"{q}"</span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="chat-messages-container">
                  {chatHistory.map((msg) => (
                    <div
                      key={msg.id}
                      className={`chat-bubble-row ${msg.sender === 'user' ? 'row-user' : 'row-assistant'}`}
                    >
                      <div className={`chat-bubble bubble-${msg.sender}`}>
                        <div className="bubble-header">
                          <span className="bubble-author">
                            {msg.sender === 'user' ? 'You' : 'VisionX Assistant'}
                          </span>
                          <span className="bubble-time">{msg.timestamp}</span>
                        </div>
                        <div className="bubble-text">
                          {msg.text.split('\n').map((paragraph, pIdx) =>
                            paragraph.trim() ? (
                              <p key={pIdx} className="bubble-paragraph">
                                {paragraph}
                              </p>
                            ) : null
                          )}
                        </div>

                        {msg.sources && msg.sources.length > 0 && (
                          <div className="bubble-sources">
                            <span className="source-label">Grounded Sources:</span>
                            {msg.sources.map((src, i) => (
                              <span key={i} className="source-chip">
                                {src}
                              </span>
                            ))}
                          </div>
                        )}

                        {msg.uncertaintyNote && (
                          <div className="verification-caveat">
                            * Note: {msg.uncertaintyNote}
                          </div>
                        )}

                        {msg.sender === 'assistant' && msg.suggestedQuestions && msg.suggestedQuestions.length > 0 && (
                          <div className="suggested-followups-container">
                            <div className="source-label" style={{ marginBottom: '6px', marginTop: '4px' }}>
                              SUGGESTED FOLLOW-UPS:
                            </div>
                            <div className="suggested-questions-list">
                              {msg.suggestedQuestions.map((sq, sqIdx) => (
                                <button
                                  key={sqIdx}
                                  type="button"
                                  className="suggested-q-btn"
                                  onClick={() => handleAskAssistant(sq)}
                                  disabled={assistantLoading}
                                  style={{ padding: '8px 12px', fontSize: '0.82rem' }}
                                >
                                  <span>"{sq}"</span>
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {assistantLoading && (
                    <div className="chat-bubble-row row-assistant">
                      <div className="chat-bubble bubble-assistant bubble-loading">
                        <span className="typing-dot" />
                        <span className="typing-dot" />
                        <span className="typing-dot" />
                        <span className="loading-label">Thinking with Strands Agent...</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Drawer Input Bar with Whistle Voice Input */}
            <div className="drawer-input-wrapper">
              {voiceError && (
                <div className="voice-error-tooltip">
                  <AlertCircle size={14} />
                  <span>{voiceError}</span>
                  <button
                    type="button"
                    onClick={() => setVoiceError(null)}
                    className="voice-err-dismiss"
                    aria-label="Dismiss error"
                  >
                    ×
                  </button>
                </div>
              )}

              {isRecordingVoice && (
                <div className="voice-recording-indicator">
                  <span className="recording-pulse-dot" />
                  <span>Recording speech... Click mic or Stop when done.</span>
                </div>
              )}

              {isTranscribingVoice && (
                <div className="voice-transcribing-indicator">
                  <RefreshCw size={14} className="spin-icon" />
                  <span>Transcribing with Cactus Compute Whistle...</span>
                </div>
              )}

              <form
                className="drawer-input-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  handleAskAssistant(assistantInput);
                }}
              >
                <input
                  type="text"
                  className="drawer-input-field"
                  placeholder={
                    isRecordingVoice
                      ? 'Listening to speech...'
                      : isTranscribingVoice
                      ? 'Transcribing speech...'
                      : selectedObject
                      ? `Ask about ${selectedObject.display_name}...`
                      : 'Ask about waste sorting...'
                  }
                  value={assistantInput}
                  onChange={(e) => setAssistantInput(e.target.value)}
                  disabled={assistantLoading || isTranscribingVoice}
                />

                {/* Microphone Button (Whistle STT) */}
                <button
                  type="button"
                  className={`drawer-mic-btn ${isRecordingVoice ? 'recording' : ''}`}
                  onClick={isRecordingVoice ? stopVoiceRecording : startVoiceRecording}
                  disabled={assistantLoading || isTranscribingVoice}
                  title={isRecordingVoice ? 'Stop recording speech' : 'Voice input (Whistle STT)'}
                  aria-label={isRecordingVoice ? 'Stop recording speech' : 'Record voice with Whistle'}
                >
                  {isRecordingVoice ? (
                    <Square size={16} strokeWidth={2.5} fill="currentColor" />
                  ) : (
                    <Mic size={18} strokeWidth={2.5} />
                  )}
                </button>

                <button
                  type="submit"
                  className="drawer-send-btn"
                  disabled={assistantLoading || isTranscribingVoice || !assistantInput.trim()}
                  aria-label="Send question to assistant"
                >
                  <Send size={18} strokeWidth={2.5} />
                </button>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
