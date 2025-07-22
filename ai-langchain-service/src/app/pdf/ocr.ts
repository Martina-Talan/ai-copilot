import * as pdfjsLib from 'pdfjs-dist/legacy/build/pdf';
import Tesseract from 'tesseract.js';
import { NodeCanvasFactory } from '../utils/nodeCanvasFactory';

export async function extractTextWithFallback(page: pdfjsLib.PDFPageProxy, pageNumber: number): Promise<string> {
  const textContent = await page.getTextContent();

  const hasText = textContent.items.some((item: any) => item.str?.trim());
  if (hasText) {
    return textContent.items.map((item: any) => item.str).join(' ').trim();
  }

  console.warn(`Page ${pageNumber} has no text – using OCR fallback`);

  const viewport = page.getViewport({ scale: 2.0 });
  const canvasFactory = new NodeCanvasFactory();
  const { canvas, context } = canvasFactory.create(viewport.width, viewport.height);

  await page.render({
    canvasContext: context,
    viewport,
    canvasFactory,
  }).promise;

  const imageBuffer = canvas.toBuffer();

  const ocrResult = await Tesseract.recognize(imageBuffer, 'deu+eng', {
    logger: (m: any) => console.log(`[OCR Page ${pageNumber}]`, m),
  });

  return ocrResult.data.text.trim();
}
