import type { TranscribeApiResponse } from '../../types';
import { getApiUrl } from '../../lib/apiConfig';

export class TranscriptionService {
  /**
   * Sends audio blob recorded by the browser to backend Whistle speech-to-text service.
   */
  public static async transcribe(audioBlob: Blob): Promise<TranscribeApiResponse> {
    const formData = new FormData();
    const extension = audioBlob.type.includes('wav')
      ? 'recording.wav'
      : audioBlob.type.includes('ogg')
      ? 'recording.ogg'
      : 'recording.webm';

    formData.append('file', audioBlob, extension);

    const targetUrl = getApiUrl('/api/transcribe');
    try {
      const response = await fetch(targetUrl, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let errDetail = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errJson = await response.json();
          if (errJson.detail) errDetail = errJson.detail;
        } catch {
          // ignore json parse error
        }
        return {
          success: false,
          text: '',
          error: `Transcription service error (${errDetail})`,
        };
      }

      const data: TranscribeApiResponse = await response.json();
      return data;
    } catch (networkErr: any) {
      // Fallback direct localhost attempt if proxied request failed
      try {
        const fallbackRes = await fetch('http://127.0.0.1:8000/api/transcribe', {
          method: 'POST',
          body: formData,
        });
        if (fallbackRes.ok) {
          return await fallbackRes.json();
        }
      } catch {
        // ignore
      }

      return {
        success: false,
        text: '',
        error: `Could not connect to transcription backend: ${networkErr.message || networkErr}`,
      };
    }
  }
}
