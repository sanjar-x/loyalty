/**
 * Lock the smart re-upload cleanup branch (F-2.3 audit, 2026-05-09).
 *
 * Scenario A — happy path: re-uploading the same localId after a crop
 * issues a single `deleteMedia(prevStorageObjectId)` call once the
 * second confirm/SSE chain lands. Regressions that drop the cleanup
 * branch would silently leak orphans in ImageBackend.
 *
 * Mocks @/entities/product so we don't touch fetch / EventSource.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';

let storageCounter = 0;
const reserveMock = vi.fn(async () => {
  storageCounter += 1;
  return {
    presignedUrl: `https://s3/upload-${storageCounter}?sig=x`,
    storageObjectId: `sid-${storageCounter}`,
  };
});
const uploadToS3Mock = vi.fn(async () => undefined);
const confirmMediaMock = vi.fn(async () => undefined);
const subscribeMediaStatusMock = vi.fn(async () => ({
  status: 'COMPLETED',
  url: 'https://cdn/processed.webp',
}));
const fetchImageAsFileMock = vi.fn(async () => ({
  name: 'fallback.jpg',
  type: 'image/jpeg',
}));
const extractRawUrlMock = vi.fn((presigned) => presigned.replace(/\?.*$/, ''));
const deleteMediaMock = vi.fn(async () => undefined);

vi.mock('@/entities/product', async () => {
  const actual = await vi.importActual('@/entities/product');
  return {
    ...actual,
    reserveMediaUpload: (...args) => reserveMock(...args),
    uploadToS3: (...args) => uploadToS3Mock(...args),
    confirmMedia: (...args) => confirmMediaMock(...args),
    subscribeMediaStatus: (...args) => subscribeMediaStatusMock(...args),
    fetchImageAsFile: (...args) => fetchImageAsFileMock(...args),
    extractRawUrl: (...args) => extractRawUrlMock(...args),
    deleteMedia: (...args) => deleteMediaMock(...args),
  };
});

import useImageUpload from '../useImageUpload';

afterEach(() => {
  storageCounter = 0;
  reserveMock.mockClear();
  uploadToS3Mock.mockClear();
  confirmMediaMock.mockClear();
  subscribeMediaStatusMock.mockClear();
  fetchImageAsFileMock.mockClear();
  extractRawUrlMock.mockClear();
  deleteMediaMock.mockClear();
});

function makeImage(name = 'photo.jpg') {
  // Vitest jsdom provides a real File constructor.
  return {
    localId: `local-${name}`,
    file: new File(['x'], name, { type: 'image/jpeg' }),
    url: `blob:fake/${name}`,
    alt: name,
    source: 'file',
  };
}

describe('useImageUpload — smart re-upload at crop (F-2.3 lock)', () => {
  it('issues deleteMedia(prev) only after the second upload completes', async () => {
    const { result } = renderHook(() => useImageUpload());
    const image = makeImage('a.jpg');

    // First upload — locks scenario A's "completed" state with sid-1.
    await act(async () => {
      await result.current.startUpload(image);
    });
    await waitFor(() => {
      expect(result.current.uploads[image.localId]?.status).toBe('completed');
    });
    expect(result.current.uploads[image.localId].storageObjectId).toBe('sid-1');

    // Crop → re-upload with the same localId. New storage id = sid-2.
    // Mock returns sequential ids so we can assert deleteMedia(sid-1).
    await act(async () => {
      await result.current.startUpload(image);
    });
    await waitFor(() => {
      expect(result.current.uploads[image.localId].storageObjectId).toBe(
        'sid-2',
      );
    });

    expect(deleteMediaMock).toHaveBeenCalledTimes(1);
    expect(deleteMediaMock).toHaveBeenCalledWith('sid-1');
  });

  it('does not call deleteMedia when there is no previous storageObjectId', async () => {
    const { result } = renderHook(() => useImageUpload());
    await act(async () => {
      await result.current.startUpload(makeImage('first.jpg'));
    });
    expect(deleteMediaMock).not.toHaveBeenCalled();
  });

  it('removeUpload aborts SSE and deletes the current storage id', async () => {
    const { result } = renderHook(() => useImageUpload());
    const image = makeImage('b.jpg');
    await act(async () => {
      await result.current.startUpload(image);
    });
    await waitFor(() => {
      expect(result.current.uploads[image.localId]?.status).toBe('completed');
    });
    deleteMediaMock.mockClear();

    act(() => {
      result.current.removeUpload(image.localId);
    });

    expect(deleteMediaMock).toHaveBeenCalledWith('sid-1');
    expect(result.current.uploads[image.localId]).toBeUndefined();
  });
});
