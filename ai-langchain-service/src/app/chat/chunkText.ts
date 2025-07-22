import { Document } from 'langchain/document';
import { RecursiveCharacterTextSplitter } from 'langchain/text_splitter';
import { encoding_for_model } from 'tiktoken';

export async function splitText(text: string, documentId: string): Promise<Document[]> {

  const cleanText = text.trim();
  if (!cleanText) {
    console.warn("Received empty or blank text.");
    return [];
  }

  const encoder = await encoding_for_model("text-embedding-ada-002");

  if (cleanText.includes("§")) {
    const sections = cleanText.split(/(?=§\d+)/g).filter(s => s.trim());

    const docs = sections.map((section, i) => new Document({
      pageContent: section.trim(),
      metadata: {
        section: `§${i + 1}`,
        documentId: String(documentId),
        chunkType: "section"
      }
    }));

    const validDocs = docs.filter(doc => {
      const tokens = encoder.encode(doc.pageContent);
      const isValid = tokens.length > 0 && tokens.length <= 8192;
      if (!isValid) {
        console.warn(`Skipping chunk §${doc.metadata.section} with ${tokens.length} tokens`);
      }
      return isValid;
    });

    return validDocs;
  }

  const splitter = new RecursiveCharacterTextSplitter({
    chunkSize: 1000,
    chunkOverlap: 200,
    separators: ["\n\n", "\n", " ", ""]
  });

  try {
    const docs = await splitter.createDocuments([cleanText]);

    const finalDocs = docs.map((doc, i) => new Document({
      pageContent: doc.pageContent,
      metadata: {
        section: `chunk-${i + 1}`,
        documentId: String(documentId),
        chunkType: "recursive"
      }
    }));

    return finalDocs;
  } catch (error) {
    console.error("Recursive splitter failed:", error);

    return [new Document({
      pageContent: cleanText,
      metadata: {
        section: "full-text",
        documentId: String(documentId),
        chunkType: "full"
      }
    })];
  }
}
