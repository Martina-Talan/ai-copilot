import { getEmbeddings } from '../../../src/app/vector/getEmbedings';
import { OpenAIEmbeddings } from '@langchain/openai';
import { saveToFaiss } from '../../../src/app/vector/vectorStore';
import fs from 'fs/promises';

jest.mock('@langchain/openai', () => ({
  OpenAIEmbeddings: jest.fn().mockImplementation(() => ({
    embedDocuments: jest.fn().mockResolvedValue(['embedded1', 'embedded2'])
  }))
}));

jest.mock('../../../src/app/vector/vectorStore', () => ({
  saveToFaiss: jest.fn()
}));

jest.mock('fs/promises', () => ({
  mkdir: jest.fn(),
  writeFile: jest.fn()
}));

describe('getEmbeddings', () => {
  const chunks = ['Text chunk 1', 'Text chunk 2'];
  const metadata = [
    { documentId: '123', chunkId: 'a' },
    { documentId: '123', chunkId: 'b' }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should embed documents and save data', async () => {
    const result = await getEmbeddings(chunks, metadata);

    expect(OpenAIEmbeddings).toHaveBeenCalled();
    const instance = (OpenAIEmbeddings as jest.Mock).mock.results[0].value;
    expect(instance.embedDocuments).toHaveBeenCalledWith(chunks);

    expect(saveToFaiss).toHaveBeenCalledWith(chunks, metadata);
    expect(fs.mkdir).toHaveBeenCalledWith('./vector-data', { recursive: true });
    expect(fs.writeFile).toHaveBeenCalledWith(
      './vector-data/chunks.json',
      expect.stringContaining('Text chunk 1'),
      'utf-8'
    );

    expect(result).toEqual(['embedded1', 'embedded2']);
  });

  it('should throw error if multiple documentIds are detected', async () => {
    const invalidMetadata = [
      { documentId: '123' },
      { documentId: '456' }
    ];

    await expect(getEmbeddings(chunks, invalidMetadata)).rejects.toThrow(
      "Chunks from multiple documents detected. Each getEmbeddings() call must process only one document."
    );

    expect(saveToFaiss).not.toHaveBeenCalled();
    expect(fs.writeFile).not.toHaveBeenCalled();
  });
});
