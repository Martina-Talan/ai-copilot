import { OpenAIEmbeddings } from '@langchain/openai';
import { saveToFaiss } from './vectorStore';
import fs from 'fs/promises';

export async function getEmbeddings(chunks: string[], metadata: any[]) {

  const uniqueDocumentIds = new Set(metadata.map((m) => m.documentId));

  if (uniqueDocumentIds.size > 1) {
    throw new Error("Chunks from multiple documents detected. Each getEmbeddings() call must process only one document.");
  }

  const embeddings = new OpenAIEmbeddings({
    openAIApiKey: process.env.OPENAI_API_KEY,
  });

  const embedded = await embeddings.embedDocuments(chunks);

  await saveToFaiss(chunks, metadata);

  const docs = chunks.map((chunk, i) => ({
    pageContent: chunk,
    metadata: metadata[i],
  }));

  await fs.mkdir('./vector-data', { recursive: true });
  await fs.writeFile('./vector-data/chunks.json', JSON.stringify(docs, null, 2), 'utf-8');

  return embedded;
}
