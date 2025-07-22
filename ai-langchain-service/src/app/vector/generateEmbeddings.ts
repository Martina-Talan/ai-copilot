import { Request, Response } from 'express';
import fs from 'fs';
import * as pdfjsLib from 'pdfjs-dist';
import { getEmbeddings } from './getEmbedings';
import { extractTextWithFallback } from '../pdf/ocr';
import { splitText } from '../chat/chunkText';

export async function generateEmbeddings(req: Request, res: Response) {
    const { path, filename, id } = req.body;
  
    try {
      const dataBuffer = fs.readFileSync(path);
      const pdf = await pdfjsLib.getDocument(dataBuffer).promise;
      const numPages = pdf.numPages;
  
      const docs: { pageContent: string; metadata: Record<string, any> }[] = [];
  
      for (let pageNum = 1; pageNum <= numPages; pageNum++) {
        const page = await pdf.getPage(pageNum);
        const pageText = await extractTextWithFallback(page, pageNum);
      
        const chunks = await splitText(pageText, String(id));
      
        chunks.forEach((chunk) => {
          const metadata = {
            documentId: String(id),
            ...chunk.metadata,
            filename,
            pageNumber: pageNum,
          };
          docs.push({
            pageContent: chunk.pageContent,
            metadata
          });
        });
      }
  
      await getEmbeddings(
        docs.map(d => d.pageContent),
        docs.map(d => d.metadata)
      );
  
      res.json({ message: 'Embeddings saved with accurate page numbers' });
  
    } catch (err) {
      console.error('PDF processing failed:', err);
      res.status(500).json({ error: 'Failed to extract PDF pages' });
    }
  };