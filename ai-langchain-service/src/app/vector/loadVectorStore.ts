import { FaissStore } from '@langchain/community/vectorstores/faiss';
import { OpenAIEmbeddings } from '@langchain/openai';

const embeddings = new OpenAIEmbeddings({
  openAIApiKey: process.env.OPENAI_API_KEY,
});

export async function loadFaissStore(documentId: string | number) {
  const dir = `faiss_index/doc_${documentId}`;
  const store = await FaissStore.load(dir, embeddings);
  return store;
}

