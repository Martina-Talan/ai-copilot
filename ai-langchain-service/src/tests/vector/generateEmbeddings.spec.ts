import { Request, Response } from 'express';
import { generateEmbeddings } from '../../../src/app/vector/generateEmbeddings';
import * as fs from 'fs';
import * as pdfjsLib from 'pdfjs-dist';
import { extractTextWithFallback } from '../../../src/app/pdf/ocr';
import { splitText } from '../../../src/app/chat/chunkText';
import { getEmbeddings } from '../../../src/app/vector/getEmbedings';

jest.mock('fs');
jest.mock('pdfjs-dist');
jest.mock('../../../src/app/pdf/ocr');
jest.mock('../../../src/app/chat/chunkText');
jest.mock('../../../src/app/vector/getEmbedings');

describe('generateEmbeddings', () => {
  const mockReq = {
    body: {
      path: 'fake.pdf',
      filename: 'fake.pdf',
      id: '123'
    }
  } as Request;

  const mockRes = {
    json: jest.fn(),
    status: jest.fn().mockReturnThis()
  } as unknown as Response;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should process PDF and call getEmbeddings', async () => {
    (fs.readFileSync as jest.Mock).mockReturnValue(Buffer.from('fake pdf'));

    const mockGetPage = jest.fn().mockResolvedValue({
      getTextContent: jest.fn(),
    });

    (pdfjsLib.getDocument as jest.Mock).mockReturnValue({
      promise: Promise.resolve({
        numPages: 1,
        getPage: mockGetPage
      })
    });

    (extractTextWithFallback as jest.Mock).mockResolvedValue('This is text from OCR.');
    (splitText as jest.Mock).mockResolvedValue([
      {
        pageContent: 'Chunk 1',
        metadata: { chunkId: 'c1' }
      }
    ]);

    (getEmbeddings as jest.Mock).mockResolvedValue(undefined);

    await generateEmbeddings(mockReq, mockRes);

    expect(extractTextWithFallback).toHaveBeenCalledTimes(1);
    expect(splitText).toHaveBeenCalledTimes(1);
    expect(getEmbeddings).toHaveBeenCalledWith(
      ['Chunk 1'],
      [expect.objectContaining({ pageNumber: 1, filename: 'fake.pdf' })]
    );
    expect(mockRes.json).toHaveBeenCalledWith({
      message: 'Embeddings saved with accurate page numbers'
    });
  });

  it('should return 500 on error', async () => {
    (fs.readFileSync as jest.Mock).mockImplementation(() => {
      throw new Error('read error');
    });

    await generateEmbeddings(mockReq, mockRes);

    expect(mockRes.status).toHaveBeenCalledWith(500);
    expect(mockRes.json).toHaveBeenCalledWith({
      error: 'Failed to extract PDF pages'
    });
  });
});
