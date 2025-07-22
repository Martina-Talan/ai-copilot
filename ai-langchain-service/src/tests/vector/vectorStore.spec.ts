import { saveToFaiss } from '../../../src/app/vector/vectorStore';
import { FaissStore } from '@langchain/community/vectorstores/faiss';

jest.mock('@langchain/community/vectorstores/faiss', () => ({
  FaissStore: {
    fromDocuments: jest.fn(),
  }
}));

const mockSave = jest.fn();
const mockMerge = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();

  (FaissStore.fromDocuments as jest.Mock).mockImplementation(async () => ({
    save: mockSave,
    mergeFrom: mockMerge,
  }));
});

describe('saveToFaiss', () => {
  const texts = ['A', 'B', 'C', 'D', 'E'];
  const metadatas = texts.map((text, i) => ({
    documentId: '123',
    chunkId: i,
  }));

  it('should save batched documents to FAISS', async () => {
    await saveToFaiss(texts, metadatas, 'test_faiss_dir');

    expect(FaissStore.fromDocuments).toHaveBeenCalledTimes(2);
    expect(mockMerge).toHaveBeenCalledTimes(1);
    expect(mockSave).toHaveBeenCalledWith('test_faiss_dir/doc_123');
    expect(mockSave).toHaveBeenCalledWith('test_faiss_dir');
  });

  it('should throw if lengths mismatch', async () => {
    await expect(saveToFaiss(['A'], [])).rejects.toThrow("texts.length !== metadatas.length");
  });

  it('should throw if documentId is missing', async () => {
    const invalidMeta = [{ chunkId: 1 }];
    await expect(saveToFaiss(['A'], invalidMeta)).rejects.toThrow("Document id not found");
  });

  it('should throw if faissStore is never created', async () => {
    (FaissStore.fromDocuments as jest.Mock).mockResolvedValueOnce(null);
    await expect(saveToFaiss(['A'], [{ documentId: '123' }])).rejects.toThrow("FAISS store not created.");
  });
});
