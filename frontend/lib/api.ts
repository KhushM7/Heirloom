const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

export interface UploadInitRequest {
  profile_id: string;
  file_name: string;
  mime_type: string;
  bytes: number;
}

export interface UploadInitResponse {
  upload_url: string;
  object_key: string;
  object_id: string;
  expires_in: number;
  max_bytes: number;
}

export interface UploadConfirmRequest {
  profile_id: string;
  object_id?: string;
  object_key: string;
  file_name: string;
  mime_type: string;
  bytes: number;
}

export interface UploadConfirmResponse {
  media_asset_id: string;
  job_id: string;
  bytes: number;
}

export interface MediaAssetOut {
  id: string;
  profile_id: string;
  file_name: string;
  mime_type: string;
  bytes: number;
}

export interface MemoryUnitOut {
  id: string;
  profile_id: string;
  media_asset_id: string;
  title: string | null;
  summary: string | null;
  description: string | null;
  event_type: string | null;
  places: string[];
  dates: string[];
  keywords: string[];
}

export interface JobOut {
  id: string;
  profile_id: string;
  media_asset_id: string | null;
  job_type: string;
  status: string;
  attempt: number;
  error_detail: string | null;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface AskRequest {
  question: string;
}

export interface AskResponse {
  answer_text: string;
  source_urls: string[];
}

export interface AskVoiceResponse {
  answer_text: string;
  source_urls: string[];
  audio_base64: string;
  audio_mime_type: string;
}

export interface ProfileCreateRequest {
  profile_id?: string;
  name?: string;
  date_of_birth?: string;
  voice_id?: string;
}

export interface ProfileOut {
  id: string;
  name: string | null;
  date_of_birth: string | null;
  voice_id?: string | null;
}

export interface MemoryUnitUpdateRequest {
  title?: string;
  description?: string;
  places?: string[];
  dates?: string[];
}

async function apiRequest<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${API_PREFIX}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

export async function initUpload(data: UploadInitRequest): Promise<UploadInitResponse> {
  return apiRequest('/media-assets/upload-init', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function confirmUpload(data: UploadConfirmRequest): Promise<UploadConfirmResponse> {
  return apiRequest('/media-assets/upload-confirm', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function uploadToS3(url: string, file: File): Promise<void> {
  const response = await fetch(url, {
    method: 'PUT',
    body: file,
    headers: {
      'Content-Type': file.type,
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to upload file to S3');
  }
}

export async function getMediaAssets(profileId: string): Promise<MediaAssetOut[]> {
  return apiRequest(`/profiles/${profileId}/media-assets`);
}

export async function getMemoryUnits(mediaAssetId: string): Promise<MemoryUnitOut[]> {
  return apiRequest(`/media-assets/${mediaAssetId}/memory-units`);
}

export async function getJobs(profileId: string): Promise<JobOut[]> {
  return apiRequest(`/profiles/${profileId}/jobs`);
}

export async function getJob(jobId: string): Promise<JobOut> {
  return apiRequest(`/jobs/${jobId}`);
}

export async function askQuestion(profileId: string, question: string): Promise<AskResponse> {
  return apiRequest(`/profiles/${profileId}/ask`, {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
}

export async function askQuestionWithVoice(
  profileId: string,
  question: string,
  voiceId?: string
): Promise<AskVoiceResponse> {
  return apiRequest(`/profiles/${profileId}/ask-voice`, {
    method: 'POST',
    body: JSON.stringify({ question, voice_id: voiceId }),
  });
}

export async function createProfile(data: ProfileCreateRequest): Promise<ProfileOut> {
  return apiRequest('/profiles', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function cloneVoiceSample(sample: File, name?: string): Promise<{ voice_id: string }> {
  const formData = new FormData();
  formData.append('sample', sample);
  if (name) {
    formData.append('name', name);
  }

  const response = await fetch(`${API_BASE}${API_PREFIX}/profiles/voice-clone`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

export async function updateMemoryUnits(
  mediaAssetId: string,
  data: MemoryUnitUpdateRequest
): Promise<MemoryUnitOut[]> {
  return apiRequest(`/media-assets/${mediaAssetId}/memory-units`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}
