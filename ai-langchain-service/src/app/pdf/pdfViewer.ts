import { Request, Response } from 'express';
import fs from 'fs';
import * as pdfjsLib from 'pdfjs-dist';

export async function handleViewPdf(req: Request, res: Response) {
  const { path } = req.body;

  try {
    const dataBuffer = fs.readFileSync(path);
    const pdf = await pdfjsLib.getDocument(dataBuffer).promise;
    const numPages = pdf.numPages;

    const pages = [];

    for (let i = 1; i <= numPages; i++) {
      const page = await pdf.getPage(i);
      const textContent = await page.getTextContent();
      
      const pageText = textContent.items
        .map(item => 'str' in item ? item.str : '')
        .join(' ')
        .replace(/\s+/g, ' ')
        .trim();

      pages.push({
        pageNumber: i,
        content: pageText,
        totalPages: numPages,
        pageIndicator: `Page ${i}/${numPages}`
      });
    }

    res.json({ pages });

  } catch (err) {
    console.error('Pdf error', err);
    res.status(500).json({ error: 'Failed to extract PDF pages' });
  }
}
