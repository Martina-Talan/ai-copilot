import { FaissStore } from '@langchain/community/vectorstores/faiss';
import { OpenAIEmbeddings } from '@langchain/openai';
import { Document } from 'langchain/document';

const embeddings = new OpenAIEmbeddings({ openAIApiKey: process.env.OPENAI_API_KEY });

export async function saveToFaiss(texts: string[], metadatas: any[], dir = "faiss_index") {

  if (texts.length !== metadatas.length) {
    console.error("texts.length !== metadatas.length");
    throw new Error("texts.length !== metadatas.length");
  }

  const batchSize = 3;

  const docs: Document[] = texts.map((txt, i) => new Document({
    pageContent: txt,
    metadata: { ...metadatas[i], documentId: String(metadatas[i].documentId) },
  }));

  let faissStore: FaissStore | null = null;

  for (let i = 0; i < docs.length; i += batchSize) {
    const batch = docs.slice(i, i + batchSize);

    const batchStore = await FaissStore.fromDocuments(batch, embeddings);

    if (!faissStore) {
      faissStore = batchStore;
    } else {
      await faissStore.mergeFrom(batchStore);
    }
  }

  if (!faissStore) {
    throw new Error("FAISS store not created.");
  }

const documentId = metadatas[0]?.documentId;
if (!documentId) {
  throw new Error("Document id not found");
}

const targetDir = `${dir}/doc_${documentId}`;

await faissStore.save(targetDir);
  await faissStore.save(dir);
}
