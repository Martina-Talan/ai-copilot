import { splitText } from '../../../src/app/chat/chunkText';
import { Document } from 'langchain/document';

jest.mock('tiktoken', () => ({
  encoding_for_model: jest.fn().mockResolvedValue({
    encode: (text: string) => Array.from({ length: text.length }, (_, i) => i),
  }),
}));

describe('splitText', () => {
  const docId = '123';

  it('should split text by sections when §§ present', async () => {
    const input = "§1 First section text. §2 Second section text.";
    const result = await splitText(input, docId);

    expect(result).toHaveLength(2);
    expect(result[0]).toBeInstanceOf(Document);
    expect(result[0].pageContent).toContain('First section');
    expect(result[0].metadata.section).toBe('§1');
  });

  it('should use recursive splitter when no § is present', async () => {
    const input = "This is some long text without any special sections. ".repeat(20);
    const result = await splitText(input, docId);

    expect(result.length).toBeGreaterThan(1);
    expect(result[0].metadata.chunkType).toBe('recursive');
  });

  it('should return empty array for blank input', async () => {
    const result = await splitText("   ", docId);
    expect(result).toEqual([]);
  });

  it('should fallback to single full-text document on splitter error', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
    const input = "This will break";

    const { RecursiveCharacterTextSplitter } = await import('langchain/text_splitter');
    jest.spyOn(RecursiveCharacterTextSplitter.prototype, 'createDocuments').mockRejectedValueOnce(new Error("fail"));

    const result = await splitText(input, docId);
    expect(result).toHaveLength(1);
    expect(result[0].metadata.chunkType).toBe('full');

    jest.restoreAllMocks();
  });
});
